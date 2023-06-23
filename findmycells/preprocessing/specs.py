# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/05_preprocessing_00_specs.ipynb.

# %% auto 0
__all__ = ['PreprocessingStrategy', 'PreprocessingObject']

# %% ../../nbs/api/05_preprocessing_00_specs.ipynb 2
import numpy as np
from shapely.geometry import Polygon
from typing import List, Dict
from skimage.io import imsave

from ..core import ProcessingObject, ProcessingStrategy, DataLoader
from ..configs import DefaultConfigs
from .. import readers

# %% ../../nbs/api/05_preprocessing_00_specs.ipynb 4
class PreprocessingStrategy(ProcessingStrategy):
    
    """
    Extending the `ProcssingStrategy` base class for preprocessing as processing subtype.
    """
    
    @property
    def processing_type(self):
        return 'preprocessing'

# %% ../../nbs/api/05_preprocessing_00_specs.ipynb 5
class PreprocessingObject(ProcessingObject):
    
    """
    Extending the `ProcessingObject` base class for preprocessing as processing subtype.
    Responsible for loading the microscopy image(s) and corresponding ROI(s) for each file,
    running the specified preprocessing strategies, updating the database, and eventually 
    for saving the preprocessed images to disk for further processing steps down the line.
    
    Note: Even though the `file_ids` argument accepts (and actually expects & requires) a 
          list as input, only a single file_id will be passed to a `PreprocessingObject`
          upon initialization. This is handled in the api module of findmycells.
    """

    @property
    def processing_type(self):
        return 'preprocessing'
    
    @property
    def widget_names(self):
        widget_names = {'overwrite': 'Checkbox',
                        'autosave': 'Checkbox',
                        'show_progress': 'Checkbox'}
        return widget_names

    @property
    def descriptions(self):
        descriptions = {'overwrite': 'overwrite previously processed files',
                        'autosave': 'autosave progress after each file',
                        'show_progress': 'show progress bar and estimated computation time'}
        return descriptions
    
    @property
    def tooltips(self):
        return {}   
    
    
    @property
    def default_configs(self) -> DefaultConfigs:
        default_values = {'overwrite': False,
                          'autosave': True,
                          'show_progress': True}
        valid_types = {'overwrite': [bool],
                       'autosave': [bool],
                       'show_progress': [bool]}
        default_configs = DefaultConfigs(default_values = default_values, valid_types = valid_types)
        return default_configs
    
    
    def _processing_specific_preparations(self) -> None:
        self.file_id = self.file_ids[0]
        self.file_info = self.database.get_file_infos(file_id = self.file_id)
        


    def load_image_and_rois(self, microscopy_reader_configs: Dict, roi_reader_configs: Dict) -> None:
        self.preprocessed_image = self._load_microscopy_image(microscopy_reader_configs = microscopy_reader_configs)
        self.preprocessed_rois = self._load_rois(roi_reader_configs = roi_reader_configs)
        
        
        
    def _load_microscopy_image(self, microscopy_reader_configs: Dict) -> np.ndarray:
        microscopy_image_data_loader = DataLoader()
        microscopy_image_reader_class = microscopy_image_data_loader.determine_reader(file_extension = self.file_info['microscopy_filetype'],
                                                                                      data_reader_module = readers.microscopy_images)
        microscopy_image = microscopy_image_data_loader.load(data_reader_class = microscopy_image_reader_class,
                                                             filepath = self.file_info['microscopy_filepath'],
                                                             reader_configs = microscopy_reader_configs)
        return microscopy_image
    

    def _load_rois(self, roi_reader_configs: Dict) -> Dict[str, Dict[str, Polygon]]:
        if roi_reader_configs['create_rois'] == True:
            max_row_idx, max_col_idx = self.preprocessed_image.shape[1:3]
            roi_covering_whole_image = Polygon([(0, 0),
                                                (max_row_idx, 0),
                                                (max_row_idx, max_col_idx),
                                                (0, max_col_idx),
                                                (0, 0)])
            if roi_reader_configs['load_roi_ids_from_file'] == True:
                area_roi_id = self.file_info['original_filename']
            else:
                area_roi_id = '000'
            extracted_roi_data = {'all_planes': {area_roi_id: roi_covering_whole_image}}
        else:
            if self.file_info['rois_present'] ==  False:
                raise FileNotFoundError('Findmycells could not find a ROI file matching the microscopy file '
                                        f'{self.file_infos["microscopy_filepath"]}. If you don`t want to use '
                                        'ROI files for any of your images, consider checking the "Don`t use ROI '
                                        'files" option. But please note - this will then apply to all your images. '
                                        'If you wanted to use a ROI file, however, please make sure that there was '
                                        'no typo in the ROI filename. Remember: it must match EXACTLY with the '
                                        'filename of the corresponding microscopy image, which is '
                                        f'"{self.file_infos["original_filename"]}" in this case.')
            else: # means: (self.file_info['rois_present'] == True) & (roi_reader_configs['create_rois'] == False)
                roi_data_loader = DataLoader()
                roi_reader_class = roi_data_loader.determine_reader(file_extension = self.file_info['rois_filetype'],
                                                                    data_reader_module = readers.rois)
                extracted_roi_data = roi_data_loader.load(data_reader_class = roi_reader_class,
                                                          filepath = self.file_info['rois_filepath'],
                                                          reader_configs = roi_reader_configs)
        return extracted_roi_data


    def _add_processing_specific_infos_to_updates(self, updates: Dict) -> Dict:
        if self.preprocessed_image.shape[3] == 3:
            updates['RGB'] = True
        else:
            updates['RGB'] = False
        updates['total_planes'] = self.preprocessed_image.shape[0]
        return updates


    def adjust_rois(self,
                    rois_dict: Dict[str, Dict[str, Polygon]],
                    lower_row_cropping_idx: int,
                    lower_col_cropping_idx: int
                    ) -> Dict[str, Dict[str, Polygon]]:
        for plane_identifier in rois_dict.keys():
            for roi_id in rois_dict[plane_identifier].keys():
                adjusted_row_coords = [coordinates[0] - lower_row_cropping_idx for coordinates in rois_dict[plane_identifier][roi_id].boundary.coords[:]]
                adjusted_col_coords = [coordinates[1] - lower_col_cropping_idx for coordinates in rois_dict[plane_identifier][roi_id].boundary.coords[:]]
                rois_dict[plane_identifier][roi_id] = Polygon(np.asarray(list(zip(adjusted_row_coords, adjusted_col_coords))))
        return rois_dict
    
    
    def crop_rgb_zstack(self, zstack: np.ndarray, cropping_indices: Dict[str, int]) -> np.ndarray:
        min_row_idx = cropping_indices['lower_row_cropping_idx']
        max_row_idx = cropping_indices['upper_row_cropping_idx']
        min_col_idx = cropping_indices['lower_col_cropping_idx']
        max_col_idx = cropping_indices['upper_col_cropping_idx']
        return zstack[:, min_row_idx:max_row_idx, min_col_idx:max_col_idx, :]
    

    def save_preprocessed_images_on_disk(self) -> None:
        for plane_index in range(self.preprocessed_image.shape[0]):
            image = self.preprocessed_image[plane_index].astype('uint8')
            out_dir_path = self.database.project_configs.root_dir.joinpath(self.database.preprocessed_images_dir)
            filename = f'{self.file_id}-{str(plane_index).zfill(3)}.png'
            imsave(out_dir_path.joinpath(filename), image)


    def save_preprocessed_rois_in_database(self) -> None:
        self.database.import_rois_dict(file_id = self.file_id, rois_dict = self.preprocessed_rois)
