# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/06_segmentation_01_strategies.ipynb.

# %% auto 0
__all__ = ['Deepflash2SemanticSegmentationStrat', 'LosslessConversionOfDF2SemanticSegToInstanceSegWithCPStrat']

# %% ../../nbs/api/06_segmentation_01_strategies.ipynb 2
from typing import Tuple, List, Dict
from pathlib import Path, PosixPath

import numpy as np
import shutil
import tempfile
import zarr
import os
from skimage import measure, segmentation, io

from .specs import SegmentationObject, SegmentationStrategy
from ..database import Database
from ..configs import DefaultConfigs
from .. import utils

# %% ../../nbs/api/06_segmentation_01_strategies.ipynb 4
class Deepflash2SemanticSegmentationStrat(SegmentationStrategy):
    
    """
    Run semantic segmentation using deepflash2. Requires that you have already an 
    ensemble of trained models ready to use and to provide the path to the directory
    where these models can be found. If you choose to process the files in your 
    project in smaller batches (which is highly recommended, due to a huge memory
    load), make sure to run the segmentations "strategy-wise" in the processing 
    configs below before launching the processing (i.e. keep the box checked).
    """
    
    @property
    def segmentation_type(self):
        return 'semantic'

    @property
    def dropdown_option_value_for_gui(self):
        return 'Semantic segmentation using deepflash2'
    
    @property
    def default_configs(self):
        default_values = {'path_to_models': Path(os.getcwd()),
                          'compute_stats': False,
                          'clear_zarrs_in_sys_temp_dir': True}
        valid_types = {'path_to_models': [PosixPath, str],
                       'compute_stats': [bool],
                       'clear_zarrs_in_sys_temp_dir': [bool]}
        valid_options = {'path_to_models': ('')}
        default_configs = DefaultConfigs(default_values = default_values, valid_types = valid_types)
        return default_configs
        
    @property
    def widget_names(self):
        return {'path_to_models': 'FileChooser',
                'compute_stats': 'Checkbox',
                'clear_zarrs_in_sys_temp_dir': 'Checkbox'}

    @property
    def descriptions(self):
        return {'path_to_models': 'Please select the directory that contains your trained models:',
                'compute_stats': '(Re-)compute inference stats (check only if you changed models)',
                'clear_zarrs_in_sys_temp_dir': 'Attempt deleting temp. files from systems temp. dir as soon as possible'}
    
    @property
    def tooltips(self):
        return {}
    
    
    def run(self, processing_object: SegmentationObject, strategy_configs: Dict) -> SegmentationObject:
        processing_object.database = self._add_deepflash2_as_segmentation_tool(database = processing_object.database,
                                                                               strategy_configs = strategy_configs)
        self._copy_all_files_of_current_batch_to_temp_dir(database = processing_object.database, file_ids_in_batch = processing_object.file_ids)
        self._run_semantic_segmentations(database = processing_object.database)
        self._move_files(database = processing_object.database)
        if strategy_configs['clear_zarrs_in_sys_temp_dir'] == True:
            self._delete_temp_files_in_sys_tmp_dir(database = processing_object.database)
        return processing_object


    def _add_deepflash2_as_segmentation_tool(self, database: Database, strategy_configs: Dict) -> Database:
        # ToDo: replace with something that is more consistent with rest of package
        if type(strategy_configs['path_to_models']) != PosixPath:
            path_to_models = Path(strategy_configs['path_to_models'])
        else:
            path_to_models = strategy_configs['path_to_models']
        if hasattr(database, 'segmentation_tool_configs') == False:
            database.segmentation_tool_configs = {'df2': {}}
        elif 'df2' not in database.segmentation_tool_configs.keys():
            database.segmentation_tool_configs['df2'] = {}
        database.segmentation_tool_configs['df2']['ensemble_path'] = path_to_models
        n_models_found = len([elem for elem in utils.list_dir_no_hidden(path_to_models) if elem.name.endswith('.pth')])
        database.segmentation_tool_configs['df2']['n_models'] = n_models_found
        if 'stats' not in database.segmentation_tool_configs['df2'].keys():
            database.segmentation_tool_configs['df2']['stats'] = self._compute_stats(database = database)
        elif strategy_configs['compute_stats'] == True:
            database.segmentation_tool_configs['df2']['stats'] = self._compute_stats(database = database)
        return database


    def _copy_all_files_of_current_batch_to_temp_dir(self, database: Database, file_ids_in_batch: List[str]) -> None:
        root_dir_path = database.project_configs.root_dir
        segmentation_tool_dir = root_dir_path.joinpath(database.segmentation_tool_dir)
        temp_copies_path = segmentation_tool_dir.joinpath('copies_of_preprocessed_images')
        for file_id in file_ids_in_batch:
            preprocessed_images_dir = root_dir_path.joinpath(database.preprocessed_images_dir)
            files_to_segment = [filepath for filepath in utils.list_dir_no_hidden(preprocessed_images_dir) if filepath.name.startswith(file_id)]
            if len(files_to_segment) > 0:
                if temp_copies_path.is_dir() == False:
                    temp_copies_path.mkdir()
                for filepath_source in files_to_segment:
                    shutil.copy(filepath_source, temp_copies_path)
                    
                    
    def _compute_stats(self, database: Database) -> Tuple:
        from deepflash2.learner import EnsembleLearner
        preprocessed_images_dir_path = database.project_configs.root_dir.joinpath(database.preprocessed_images_dir)
        expected_file_count = sum(database.file_infos['total_planes'])
        actual_file_count = len([filepath for filepath in utils.list_dir_no_hidden(preprocessed_images_dir_path) if filepath.name.endswith('.png')])
        if actual_file_count != expected_file_count:
            raise ValueError('Actual and expected counts of preprocessed images don´t match.')
        ensemble_learner = EnsembleLearner(image_dir = preprocessed_images_dir_path, 
                                           ensemble_path = database.segmentation_tool_configs['df2']['ensemble_path'])
        stats = ensemble_learner.stats
        del ensemble_learner
        return stats


    def _run_semantic_segmentations(self, database: Database) -> None:
        from deepflash2.learner import EnsembleLearner
        segmentation_tool_dir_path = database.project_configs.root_dir.joinpath(database.segmentation_tool_dir)
        segmentation_tool_temp_dir_path = segmentation_tool_dir_path.joinpath(database.segmentation_tool_temp_dir)
        image_dir = segmentation_tool_dir_path.joinpath('copies_of_preprocessed_images')
        ensemble_learner = EnsembleLearner(image_dir = image_dir,
                                           ensemble_path = database.segmentation_tool_configs['df2']['ensemble_path'],
                                           stats = database.segmentation_tool_configs['df2']['stats'])
        ensemble_learner.get_ensemble_results(ensemble_learner.files, 
                                              zarr_store = segmentation_tool_temp_dir_path,
                                              export_dir = segmentation_tool_dir_path,
                                              use_tta = True)
        del ensemble_learner


    def _move_files(self, database: Database) -> None:
        semantic_segmentations_target_dir_path = database.project_configs.root_dir.joinpath(database.semantic_segmentations_dir)
        segmentation_tool_dir_path = database.project_configs.root_dir.joinpath(database.segmentation_tool_dir)      
        current_semantic_masks_dir_path = segmentation_tool_dir_path.joinpath('masks')
        for mask_filepath in utils.list_dir_no_hidden(current_semantic_masks_dir_path):
            target_filepath = semantic_segmentations_target_dir_path.joinpath(mask_filepath.name)
            if target_filepath.is_file() == True:
                target_filepath.delete()
            shutil.move(str(mask_filepath), str(semantic_segmentations_target_dir_path))
        shutil.rmtree(segmentation_tool_dir_path.joinpath('copies_of_preprocessed_images'))


    def _delete_temp_files_in_sys_tmp_dir(self, database: Database) -> None:
        temp_zarr_paths = [elem for elem in Path(tempfile.gettempdir()).iterdir() if 'zarr' in elem.name]
        for dir_path in temp_zarr_paths:
            shutil.rmtree(dir_path)       

            
    def _add_strategy_specific_infos_to_updates(self, updates: Dict) -> Dict:
        updates['semantic_segmentations_done'] = True
        return updates

# %% ../../nbs/api/06_segmentation_01_strategies.ipynb 5
class LosslessConversionOfDF2SemanticSegToInstanceSegWithCPStrat(SegmentationStrategy):
    
    @property
    def segmentation_type(self):
        return 'instance'

    @property
    def dropdown_option_value_for_gui(self):
        return 'Instance segmentation using cellpose'
    
    @property
    def default_configs(self):
        default_values = {'net_avg': True,
                          'model_type': 'nuclei',
                          'diameter': 0.0}
        valid_types = {'net_avg': [bool],
                       'model_type': [str],
                       'diameter': [float]}
        valid_ranges = {'diameter': (0.0, 999_999.9, 0.1)}
        valid_options = {'model_type': ('nuclei', 'cyto')}
        default_configs = DefaultConfigs(default_values = default_values,
                                         valid_types = valid_types,
                                         valid_value_ranges = valid_ranges,
                                         valid_value_options = valid_options)
        return default_configs
        
    @property
    def widget_names(self):
        return {'net_avg': 'Checkbox',
                'model_type': 'Dropdown',
                'diameter': 'BoundedFloatText'}

    @property
    def descriptions(self):
        return {'net_avg': 'Use average result of multiple attempts (recommended)',
                'model_type': 'Select the cellpose model type to use',
                'diameter': 'Diameter of a single feature [px] (select 0 to compute automatically)'}
    
    @property
    def tooltips(self):
        return {}
    
    
    def run(self, processing_object: SegmentationObject, strategy_configs: Dict) -> SegmentationObject:
        processing_object.database = self._add_cellpose_as_segmentation_tool(database = processing_object.database,
                                                                             strategy_configs = strategy_configs)        
        self._run_instance_segmentations(segmentation_object = processing_object)
        return processing_object
        
        
    def _assert_all_semantic_segmentations_are_done(self, database: Database) -> None:
        all_file_ids = database.file_infos['file_id']
        file_ids_without_semantic_segmentations = []
        for file_id in all_file_ids:
            executed_processing_strats = list(database.file_histories[file_id].tracked_history['processing_strategy'].values)
            if 'Deepflash2SemanticSegmentationStrat' not in executed_processing_strats:
                file_ids_without_semantic_segmentations.append(file_id)
                continue
            else:
                processing_strat_idx = executed_processing_strats.index('Deepflash2SemanticSegmentationStrat')
                if database.file_histories[file_id].tracked_settings[processing_strat_idx]['semantic_segmentations_done'] == False:
                    file_ids_without_semantic_segmentations.append(file_id)
        not_all_semantic_segmentations_done_error_message = ('You can only use the in-built function to calculate the appropriate '
                                                             'diameter for cellpose for your data, if you have created the semantic '
                                                             'segmentations of all files already. However, you are currently still '
                                                             'missing the semantic segmentations of the following file IDs: '
                                                             f'{file_ids_without_semantic_segmentations}. Therefore, you have now two '
                                                             'options. 1) You simply finish all semantic segmentations first, or 2) '
                                                             'you specify the diameter cellpose is supposed to use. Note: if you '
                                                             'added both segmentation methods (deepflash2 and cellpose) to your '
                                                             'processing methods in findmycells, make sure to keep "process strategy-wise" '
                                                             'checked and to select all file IDs.')
        assert len(file_ids_without_semantic_segmentations) == 0, not_all_semantic_segmentations_done_error_message

    
    def _add_cellpose_as_segmentation_tool(self, database: Database, strategy_configs: Dict) -> Database:
        semantic_masks_dir = database.project_configs.root_dir.joinpath(database.semantic_segmentations_dir)
        if hasattr(database, 'segmentation_tool_configs') == False:
            database.segmentation_tool_configs = {'cp': {}}
        elif 'cp' not in database.segmentation_tool_configs.keys():
            database.segmentation_tool_configs['cp'] = {}
        database.segmentation_tool_configs['cp']['net_avg'] = strategy_configs['net_avg']
        database.segmentation_tool_configs['cp']['model_type'] = strategy_configs['model_type']
        if strategy_configs['diameter'] == 0:
            self._assert_all_semantic_segmentations_are_done(database = database)
            database.segmentation_tool_configs['cp']['diameter'] = self._compute_cellpose_diameter(semantic_masks_dir = semantic_masks_dir)
        else:
            database.segmentation_tool_configs['cp']['diameter'] = strategy_configs['diameter']
        return database


    def _compute_cellpose_diameter(self, semantic_masks_dir: PosixPath) -> float:
        all_median_equivalent_diameters = []
        for mask_filepath in semantic_masks_dir.iterdir():
            if mask_filepath.name.endswith('.png'):
                mask = io.imread(mask_filepath)
                median_equivalent_diameter = self._calculate_median_equivalent_diameter_of_features_in_mask(segmentation_mask = mask)
                all_median_equivalent_diameters.append(median_equivalent_diameter)
        if len(all_median_equivalent_diameters) > 0:
            cellpose_diameter = np.nanmedian(all_median_equivalent_diameters)
            if np.isnan(cellpose_diameter):
                raise ValueError('Findmycells could not determine what diameter to use for the Cellpose instance segmentations (diameter = np.NaN). '
                                 'This could happen if you a) have no semantic segmentation masks in the corresponding directory, or '
                                 'b) there were no features detected during the semantic segmentation process! Please check your semantic segmentations.')
        else:
            raise ValueError('Cellpose diameter could not be calculated, as there were no semantic segmentation masks found. Please check your semantic segmentation masks!')
        return cellpose_diameter
            

    def _calculate_median_equivalent_diameter_of_features_in_mask(self, segmentation_mask: np.ndarray) -> float:
        labeled_mask = measure.label(segmentation_mask)
        unique_label_ids, pixel_counts_per_label_id = np.unique(labeled_mask, return_counts=True)
        unique_label_ids = list(unique_label_ids)
        if 0 in unique_label_ids:
            background_label_index = unique_label_ids.index(0)
            pixel_counts_per_label_id = np.delete(pixel_counts_per_label_id, background_label_index)
        if pixel_counts_per_label_id.shape[0] > 0:
            equivalent_diameters = []
            for area_in_pixels in pixel_counts_per_label_id:
                equivalent_diameters.append(((area_in_pixels / np.pi)**0.5) * 2)
            median_equivalent_diameter = np.median(equivalent_diameters)
        else:
            median_equivalent_diameter = np.nan
        return median_equivalent_diameter


    def _run_instance_segmentations(self, segmentation_object: SegmentationObject):
        database = segmentation_object.database
        segmentation_tool_dir_path = database.project_configs.root_dir.joinpath(database.segmentation_tool_dir)
        segmentation_tool_temp_dir_path = segmentation_tool_dir_path.joinpath(database.segmentation_tool_temp_dir)
        print(segmentation_tool_temp_dir_path)
        zarr_group = zarr.open(segmentation_tool_temp_dir_path, mode='r')
        for image_filename in zarr_group['/smx'].__iter__():
            file_id = image_filename[:4]
            if file_id in segmentation_object.file_ids:
                df2_softmax = zarr_group[f'/smx/{image_filename}'][..., 1]
                df2_pred = np.zeros_like(df2_softmax)
                df2_pred[np.where(df2_softmax >= 0.5)] = 1
                # check if there was any feature predicted - if not, there is no need to run cellpose
                if df2_pred.max() == 1:
                    cp_mask = self._compute_cellpose_mask(df2_softmax = df2_softmax, 
                                                         model_type = database.segmentation_tool_configs['cp']['model_type'],
                                                         net_avg = database.segmentation_tool_configs['cp']['net_avg'],
                                                         diameter = database.segmentation_tool_configs['cp']['diameter'])            
                    instance_mask = self._lossless_conversion_of_df2_semantic_to_instance_seg_using_cp(df2_pred = df2_pred, cp_mask = cp_mask)
                else: 
                    instance_mask = df2_pred.copy()
                instance_mask = instance_mask.astype('uint16')
                filepath = database.project_configs.root_dir.joinpath(database.instance_segmentations_dir, image_filename)
                io.imsave(filepath, instance_mask, check_contrast=False)


    def _compute_cellpose_mask(self, df2_softmax: np.ndarray, model_type: str, net_avg: bool, diameter: int) -> np.ndarray:
        from torch.cuda import empty_cache
        from cellpose import models
        empty_cache()
        model = models.Cellpose(gpu = True, model_type = model_type)
        cp_mask, _, _, _ = model.eval(df2_softmax, net_avg = net_avg, augment = True, normalize = False, diameter = diameter, channels = [0,0])
        empty_cache()
        return cp_mask


    def _lossless_conversion_of_df2_semantic_to_instance_seg_using_cp(self, df2_pred: np.ndarray, cp_mask: np.ndarray) -> np.ndarray:
        lossless_converted_mask = np.zeros_like(df2_pred)
        labeled_df2_pred = measure.label(df2_pred)
        unique_df2_labels = list(np.unique(labeled_df2_pred))
        unique_df2_labels.remove(0)
        for original_df2_label in unique_df2_labels:
            black_pixels_present = self._check_if_df2_label_is_fully_covered_in_cp_mask(df2_pred = labeled_df2_pred,
                                                                                       df2_label_id = original_df2_label,
                                                                                       cp_mask = cp_mask)                                                        
            if black_pixels_present:
                lossless_converted_mask = self._fill_entire_df2_label_area_with_instance_label(df2_pred = labeled_df2_pred, 
                                                                                              df2_label_id = original_df2_label, 
                                                                                              cp_mask = cp_mask,
                                                                                              converted_mask = lossless_converted_mask)
            else:
                cp_labels_within_df2_label = np.unique(cp_mask[np.where(labeled_df2_pred == original_df2_label)])
                tmp_cp_mask = cp_mask.copy()
                tmp_cp_mask[np.where(labeled_df2_pred != original_df2_label)] = 0
                for cp_label_id in cp_labels_within_df2_label:
                    next_label_id = lossless_converted_mask.max() + 1
                    lossless_converted_mask[np.where(tmp_cp_mask == cp_label_id)] = next_label_id
        return lossless_converted_mask


    def _check_if_df2_label_is_fully_covered_in_cp_mask(self, df2_pred: np.ndarray, df2_label_id: int, cp_mask: np.ndarray) -> bool:
        cp_labels_within_df2_label = np.unique(cp_mask[np.where(df2_pred == df2_label_id)])
        if 0 in cp_labels_within_df2_label:
            black_pixels_present = True
        else:
            black_pixels_present = False
        return black_pixels_present


    def _fill_entire_df2_label_area_with_instance_label(self, df2_pred: np.ndarray, df2_label_id: int, cp_mask: np.ndarray, converted_mask: np.ndarray) -> np.ndarray:
        cp_labels_within_df2_label = list(np.unique(cp_mask[np.where(df2_pred == df2_label_id)]))
        cp_labels_within_df2_label.remove(0)
        if len(cp_labels_within_df2_label) > 0:
            expanded_cp_mask = cp_mask.copy()
            expanded_cp_mask[np.where(df2_pred != df2_label_id)] = 0
            black_pixels_present, expansion_distance = True, 0
            while black_pixels_present:
                expansion_distance += 500
                expanded_cp_mask = segmentation.expand_labels(expanded_cp_mask, distance = expansion_distance)
                black_pixels_present = self._check_if_df2_label_is_fully_covered_in_cp_mask(df2_pred = df2_pred,
                                                                                           df2_label_id = df2_label_id,
                                                                                           cp_mask = expanded_cp_mask)
            # remove all overflow pixels
            expanded_cp_mask[np.where(df2_pred != df2_label_id)] = 0
            for cp_label_id in cp_labels_within_df2_label:
                next_label_id = converted_mask.max() + 1
                converted_mask[np.where(expanded_cp_mask == cp_label_id)] = next_label_id
        else:
            next_label_id = converted_mask.max() + 1
            converted_mask[np.where(df2_pred == df2_label_id)] = next_label_id        
        return converted_mask

    def _add_strategy_specific_infos_to_updates(self, updates: Dict) -> Dict:
        updates['instance_segmentations_done'] = True
        return updates
