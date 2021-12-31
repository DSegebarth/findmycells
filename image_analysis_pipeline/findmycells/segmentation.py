from abc import ABC, abstractmethod
import os
import numpy as np
import pandas as pd
from pathlib import Path
import shutil
from PIL import Image
from typing import Tuple, List

from torch.cuda import empty_cache

from deepflash2.learner import EnsembleLearner
from deepflash2.models import get_diameters

from .database import Database


class SegmentationMethod(ABC):
    
    @abstractmethod
    def __init__(self, database: Database, file_ids: List):
        self.database = database
        self.file_ids = file_ids
    
    @abstractmethod
    def run_segmentations(self) -> Database:
        return self.database



class Deepflash2BinarySegmentation(SegmentationMethod):
    # stats can be saved! they just have to be calculated once and then predictions / segmentations can be performed on individual files!!    
    def __init__(self, database: Database):
        self.database = database
        self.image_dir = self.database.deepflash2_dir + 'temp_copies_of_prepro_images/'
        self.ensemble_path = self.database.deepflash2_configs['ensemble_path']
        self.n_models = self.database.deepflash2_configs['n_models']
        self.stats = self.database.deepflash2_configs['stats']
        # Add Warning to log if self.n_models < 3

    
    def run_segmentations(self) -> Database:         

        ensemble_learner = EnsembleLearner(image_dir = self.image_dir, ensemble_path = self.ensemble_path, stats = self.stats)
        ensemble_learner.get_ensemble_results(ensemble_learner.files, 
                                              zarr_store = self.database.deepflash2_temp_dir,
                                              export_dir = self.database.deepflash2_dir,
                                              use_tta = True)

        if self.database.deepflash2_configs['df_ens'] == None:
            self.database.deepflash2_configs['df_ens'] = ensemble_learner.df_ens.copy()
        else:
            self.database.deepflash2_configs['df_ens'] = pd.concat([self.database.deepflash2_configs['df_ens'], ensemble_learner.df_ens.copy()]) # axis?!

        if hasattr(self.database, 'segmented_file_lists') == False:
            self.database.segmented_file_lists = {'binary_segmented_files': list(),
                                                  'instance_segmented_files': list()}
        self.database.segmented_file_lists['binary_segmented_files'].append(files_to_segment)
        del ensemble_learner

        return self.database
        
        
    def clear_temp_data(self):
        # Remove all zarr directories that were created in systems tmp directory:
        temp_zarr_subdirs = [elem for elem in os.listdir('/tmp/') if 'zarr' in elem]
        if len(temp_zarr_subdirs) > 0:
            for subdirectory in temp_zarr_subdirs:
                shutil.rmtree(f'/tmp/{subdirectory}/')



class Deepflash2InstanceSegmentation(SegmentationMethod):
    # stats can be saved! they just have to be calculated once and then predictions / segmentations can be performed on individual files!!
    def __init__(self, database: Database) -> Database:
        self.database = database
        self.image_dir = self.database.deepflash2_dir + 'temp_copies_of_prepro_images/'
        self.ensemble_path = self.database.deepflash2_configs['ensemble_path']
        self.n_models = self.database.deepflash2_configs['n_models']
        self.stats = self.database.deepflash2_configs['stats']
        self.df_ens = self.database.deepflash2_configs['df_ens']
        
    
    def get_cellpose_diameter(self):
        deepflash2_masks_dir = self.database.deepflash2_dir + 'masks/'
        mask_paths = [f'{deepflash2_masks_dir}{elem}' for elem in os.listdir(deepflash2_masks_dir)]
        masks_as_arrays = []
        for mask_as_image in mask_paths:
            with Image.open(mask_as_image) as image:
                masks_as_arrays.append(np.array(image))
        cellpose_diameter = get_diameters(masks_as_arrays)
        return cellpose_diameter
    
    
    def run_segmentations(self) -> Database:
        instance_segmented_files = os.listdir(self.image_dir)
        
        cellpose_diameter = self.get_cellpose_diameter()
        if self.database.deepflash2_configs['cellpose_diameter_first_batch'] == None:
            self.database.deepflash2_configs['cellpose_diameter_first_batch'] = cellpose_diameter
        self.database.deepflash2_configs['cellpose_diameters_all_batches'].append(cellpose_diameter)
        
        empty_cache()
        for row_id in range(self.df_ens.shape[0]):
            ensemble_learner = EnsembleLearner(image_dir = self.image_dir, ensemble_path = self.ensemble_path, stats = self.stats)
            df_single_row = self.df_ens.iloc[row_id].to_frame().T.reset_index(drop=True).copy()
            ensemble_learner.df_ens = df_single_row
            ensemble_learner.cellpose_diameter = self.database.deepflash2_configs['cellpose_diameter_first_batch']
            ensemble_learner.get_cellpose_results(export_dir = self.database.deepflash2_dir)
            del ensemble_learner
            empty_cache()      
        self.database.segmented_file_lists['instance_segmented_files'] = instance_segmented_files
        
        return self.database
    
    
    def clear_temp_data(self):
        # Remove all zarr directories that were created in systems tmp directory:
        temp_zarr_subdirs = [elem for elem in os.listdir('/tmp/') if 'zarr' in elem]
        if len(temp_zarr_subdirs) > 0:
            for subdirectory in temp_zarr_subdirs:
                shutil.rmtree(f'/tmp/{subdirectory}/')

        # Remove all zarr directories that were created in designated df2 temp directory:
        shutil.rmtree(self.database.deepflash2_temp_dir[:self.database.deepflash2_temp_dir.rfind('/')])
        

class SegmentationStrategy(ABC):
    
    @abstractmethod
    def run(self, database: Database, file_ids = None) -> Database:
        return database
    
    
class Deepflash2BinaryAndInstanceSegmentationStrategy(SegmentationStrategy):

    def run(self, database: Database, file_ids = None) -> Database:
        self.database = database
        
        if all(self.database.file_infos['preprocessing_completed']) == False:
            raise TypeError('Not all files have been preprocessed yet! This has to be finished before deepflash2 can be used.')
        
        if hasattr(self.database, 'deepflash2_configs') == False:
            self.database.deepflash2_configs = {'n_models': len([elem for elem in os.listdir(self.database.trained_models_dir) if elem.endswith('.pth')]),
                                                'ensemble_path': Path(self.database.trained_models_dir),
                                                'stats': self.compute_stats(),
                                                'df_ens': None,
                                                'cellpose_diameter_first_batch': None,
                                                'cellpose_diameters_all_batches': list()}
        if file_ids == None:
            self.file_ids = self.database.file_infos['file_id']
        else:
            self.file_ids = file_ids
            
        temp_copies_dir = self.database.deepflash2_dir + 'temp_copies_of_prepro_images/'
        for file_id in self.file_ids:
            os.mkdir(temp_copies_dir)
            
            files_to_segment = [filename for filename in os.listdir(self.database.preprocessed_images_dir) if filename.startswith(file_id)]
            for file in files_to_segment:
                filepath_source = self.database.preprocessed_images_dir + file
                shutil.copy(filepath_source, temp_copies_dir)
        
            df2_binary_seg = Deepflash2BinarySegmentation(self.database)
            self.database = df2_binary_seg.run_segmentations()

            df2_instance_seg = Deepflash2InstanceSegmentation(self.database)
            self.database = df2_instance_seg.run_segmentations()
            
            # Clear all temp data before starting with next file_id
            df2_instance_seg.clear_temp_data()
            self.database.deepflash2_configs['df_ens'] = None
            shutil.rmtree(temp_copies_dir)
        
        # Has to take care that the files end up in the correct directories! -> binary_segmentations & instance_segmentations, respectively
        return self.database
        
    def compute_stats(self) -> Tuple:
        expected_file_count = sum(self.database.file_infos['total_image_planes'])
        actual_file_count = len([image for image in os.listdir(self.database.preprocessed_images_dir) if image.endswith('.png')])
        
        if actual_file_count != expected_file_count:
            raise ImportError('Actual and expected counts of preprocessed images don´t match.')
            
        ensemble_learner = EnsembleLearner(image_dir = self.database.preprocessed_images_dir, ensemble_path = self.database.deepflash2_configs['ensemble_path'])
        stats = ensemble_learner.stats
        del ensemble_learner
        return stats
            
    
class Segmentor:
    
    def __init__(self, database: Database, file_ids = None):
        self.database = database
        self.file_ids = file_ids
        
    def run_all(self) -> Database:
        self.database = self.database.segmentation_strategy.run(self.database, self.file_ids)
        
        return self.database
        
