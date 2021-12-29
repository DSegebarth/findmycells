from abc import ABC, abstractmethod
import os
import numpy as np
import pickle
from datetime import datetime

class Database():
    '''
    The database object is intended to collect and hold all information about
    the image analysis project at hand. Depending on the type of analysis that 
    shall be performed, the Database needs to be flexible and adopt to the 
    respective needs. For instance, there might be more than just two groups 
    that are investigated, or just a single group but with multiple images per 
    subject, and so on. For the moment, however, it is quite static and expects 
    a fixed structure in the project root directory:
    
    root_dir:
       |__ 00_microscopy_images:
       |        |__ group1:
       |        |      |__ subject_a:
       |        |      |      |__ microscopy_image0.czi
       |        |      |      |__ microscopy_image1.czi
       |        |      |      |__ microscopy_image2.czi
       |        |      |__ subject_b:
       |        |             |__ microscopy_image3.czi
       |        |             |__ microscopy_image4.czi
       |        |             |__ microscopy_image5.czi
       |        |__ group2:
       |               |__ subject_c:
       |               |      |__ microscopy_image6.czi
       |               |      |__ microscopy_image7.czi
       |               |      |__ microscopy_image8.czi
       |               |__ subject_d:
       |                      |__ microscopy_image9.czi
       |                      |__ microscopy_image10.czi
       |                      |__ microscopy_image11.czi
       |
       |__ 01_rois_to_analyze:
       |        |__ group1:
       |        |      |__ subject_a:
       |        |      |      |__ rois_for_image0.roi
       |        |      |      |__ rois_for_image1.roi
       |        |      |      |__ rois_for_image2.roi
       |        |      |__ subject_b:
       |        |             |__ rois_for_image3.roi
       |        |             |__ rois_for_image4.roi
       |        |             |__ rois_for_image5.roi
       |        |__ group2:
       |               |__ subject_c:
       |               |      |__ rois_for_image6.roi
       |               |      |__ rois_for_image7.roi
       |               |      |__ rois_for_image8.roi
       |               |__ subject_d:
       |                      |__ rois_for_image9.roi
       |                      |__ rois_for_image10.roi
       |                      |__ rois_for_image11.roi
       |
       |__ 02_preprocessed_images:
       |        |__ 0000_000.png (first image plane of first microscopy z-stack)
       |        |__ 0000_001.png (second image plane of first microscopy z-stack)
       |        |   ...
       |        |__ 0001_000.png (first image plane of second microscopy z-stack)
       |        |   ...
       |        |__ 0011_008.png (last image plane of last microscopy z-stack)
       |
       |__ 03_deepflash2: (could become a generic "03_processing_module" folder at some point)
       |        |__ trained_models:
       |        |      |__ model_0.pth
       |        |      |__ model_1.pth
       |        |      |   ...
       |        |      |__ model_i.pth
       |        |__ temp (will be generated)
       |        |__ masks (will be generated)
       |        |__ uncertainties (will be generated)
       |        |__ cellpose_masks (will be generated)
       |
       |__ 04_binary_segmentations:
       |        |__ 0000_000_mask.png (binary segmentation mask for first image plane of first microscopy z-stack)
       |        |   ...
       |        |__ 0011_008_mask.png (binary segmentation mask for last image plane of last microscopy z-stack)
       |
       |__ 05_instance_segmentations:
       |        |__ 0000_000_mask.png (instance segmentation mask for first image plane of first microscopy z-stack)
       |        |   ...
       |        |__ 0011_008_mask.png (instance segmentation mask for last image plane of last microscopy z-stack)
       |
       |__ 06_results:
                |__ database.xlsx (will be generated)
                |__ processing_log.txt (will be generated)
                |__ quantifications.xlsx (will be generated)
    
    '''
    
    def __init__(self, user_input_via_gui: dict):
        self.extract_user_input(user_input_via_gui)
        self.construct_main_subdirectories()
        self.create_file_infos()
        
    def extract_user_input(self, user_input: dict):
        self.root_dir = user_input['project_root_dir']
        if 'preprocessing' in user_input.keys():
            self.preprocessing_configs = user_input['preprocessing']

    def construct_main_subdirectories(self):
        # At first, ensure that all seven main subdirectories are present - if not: create the missing ones
        # Instead of searching for specific keywords, the respective directories should be chosen by the user via the GUI
        subdirectories = os.listdir(self.root_dir)
        
        # Mandatory directories (images, rois, and df2 models are required):
        self.microscopy_image_dir = self.root_dir + [elem for elem in subdirectories if 'microscopy' in elem][0] + '/'
        self.rois_to_analyze_dir = self.root_dir + [elem for elem in subdirectories if 'rois' in elem][0] + '/'
        self.deepflash2_dir = self.root_dir + [elem for elem in subdirectories if 'deepflash2' in elem][0] + '/'
        self.create_deepflash2_subdirectories()
        
        # Remaining directories that are currently not required to exist when the database object is created:
        try: self.preprocessed_images_dir = self.root_dir + [elem for elem in subdirectories if 'preprocessed' in elem][0] + '/' 
        except:
            self.preprocessed_images_dir = self.root_dir + '03_preprocessed_images/'
            os.mkdir(self.preprocessed_images_dir)                  
        
        try: self.binary_segmentations_dir = self.root_dir + [elem for elem in subdirectories if 'binary' in elem][0] + '/' 
        except:
            self.binary_segmentations_dir = self.root_dir + '04_binary_segmentations/'
            os.mkdir(self.binary_segmentations_dir)  
        
        try: self.instance_segmentations_dir = self.root_dir + [elem for elem in subdirectories if 'instance' in elem][0] + '/'
        except:
            self.instance_segmentations_dir = self.root_dir + '05_instance_segmentations/'
            os.mkdir(self.instance_segmentations_dir)
 
        try: self.results_dir = self.root_dir + [elem for elem in subdirectories if 'results' in elem][0] + '/'
        except:
            self.results_dir = self.root_dir + '06_results/'
            os.mkdir(self.results_dir)

    
    def create_deepflash2_subdirectories(self):
        deepflash2_subdirectories = os.listdir(self.deepflash2_dir)
        try: self.trained_models_dir = self.deepflash2_dir + [elem for elem in deepflash2_subdirectories if 'models' in elem][0] + '/'
        except:
            self.trained_models_dir = self.deepflash2_dir + 'trained_models/'
            os.mkdir(self.trained_models_dir)
            
        try: self.deepflash2_temp_dir = self.deepflash2_dir + [elem for elem in deepflash2_subdirectories if 'temp' in elem][0] + '/'
        except:
            self.deepflash2_temp_dir = self.deepflash2_dir + 'temp/'
            os.mkdir(self.deepflash2_temp_dir) 
        
    
    def create_file_infos(self):
        # Initial information will be retrieved from the microscopy_image_dir
        self.file_infos = {'file_id': list(),
                           'original_file_id': list(),
                           'group_id': list(),
                           'subject_id': list(),
                           'microscopy_filepath': list(),
                           'microscopy_filetype': list(),
                           'rois_present': list(),
                           'rois_filepath': list(),
                           'rois_filetype': list()}
        file_id = 0
        for group in os.listdir(self.microscopy_image_dir):
            for subject in os.listdir(self.microscopy_image_dir + group + '/'):
                for filename in os.listdir(self.microscopy_image_dir + group + '/' + subject + '/'):
                    self.file_infos['file_id'].append(str(file_id).zfill(4))
                    original_file_id = filename[:filename.find('.')]
                    self.file_infos['original_file_id'].append(original_file_id)
                    self.file_infos['group_id'].append(group)
                    self.file_infos['subject_id'].append(subject)
                    self.file_infos['microscopy_filepath'].append(f'{self.microscopy_image_dir}{group}/{subject}/{filename}')
                    self.file_infos['microscopy_filetype'].append(filename[filename.find('.'):])
                    try:
                        roi_filename = [elem for elem in os.listdir(f'{self.rois_to_analyze_dir}{group}/{subject}/') if elem.startswith(original_file_id)][0]
                        self.file_infos['rois_present'].append(True)
                        self.file_infos['rois_filepath'].append(f'{self.rois_to_analyze_dir}{group}/{subject}/{roi_filename}')
                        self.file_infos['rois_filetype'].append(roi_filename[roi_filename.find('.'):])
                    except:
                        self.file_infos['rois_present'].append(False)
                        self.file_infos['rois_filepath'].append(None)
                        self.file_infos['rois_filetype'].append(None)                        
                        # Should be written to log file                                        
                        print(f'Couldn´t find matching roi file for {original_file_id} - quantification will be performed on the whole image.')
                    file_id += 1
                
                    
    def get_file_infos(self, identifier: str):
        # supports use of either original_file_id, file_id, microscopy_filepath, or rois_filepath as input parameter identifier       
        if identifier in self.file_infos['file_id']:
            index = self.file_infos['file_id'].index(identifier)
        elif identifier in self.file_infos['original_file_id']:
            index = self.file_infos['original_file_id'].index(identifier)
        elif identifier in self.file_infos['microscopy_filepath']:
            index = self.file_infos['microscopy_filepath'].index(identifier)
        elif identifier in self.file_infos['rois_filepath']:
            index = self.file_infos['rois_filepath'].index(identifier)
        else:
            raise NameError(f'{identifier} is not a valid input!')
        
        file_infos = dict()    
        for key in self.file_infos.keys():
            if len(self.file_infos[key]) > 0:
                file_infos[key] = self.file_infos[key][index]
         
        return file_infos
    
    def add_new_key_to_file_infos(self, key, values = None):
        """
        Allows us to add a new key-value-pair to the file_infos dict
        If values is not passed, a list full of "None" that matches the length of file_ids will be created
        If values is passed, it has to be a list of the length of file_id
        """
        if key in self.file_infos.keys():
            raise ValueError("The key you are trying to add is already in file_infos.")
        
        else:
            length = len(self.file_infos['file_id'])

            if values == None:
                values = [None] * length
                self.file_infos[key] = values

            elif type(values) != list:
                raise TypeError("values has to be a list that matches the length of file_infos['file_ids']")

            else:
                if len(values) == length:
                    self.file_infos[key] = values                
                else:
                    raise ValueError("The list of values that you provided does not match the length of file_infos['file_ids']!")
            

    def update_file_infos(self, file_id: str, key: str, value):    
        self.file_infos[key][self.file_infos['file_id'].index(file_id)] = value

    
    def import_roi_polygons(self, rois_object):
        if hasattr(self, 'rois_as_shapely_polygons') == False:
            self.rois_as_shapely_polygons = dict()
            
        original_file_id = rois_object.filepath[rois_object.filepath.rfind('/') + 1 : rois_object.filepath.rfind('.')]
        file_id = self.file_infos['file_id'][self.file_infos['original_file_id'].index(original_file_id)]
        
        self.rois_as_shapely_polygons[file_id] = dict()
        for roi_id in rois_object.as_polygons.keys():
            # potential conflict when different rois are used for the individual planes. Update keys e.g. to roi_id_000 and/or plane_id_000 and/or all_planes
            self.rois_as_shapely_polygons[file_id][roi_id] = rois_object.as_polygons[roi_id]
        
    
    def save_all(self):
        """
        If not specified otherwise, all data will be stored in pickle files.
        When output_type is set to ".csv", a pandas DataFrame will be created
        from the file_infos dictionary and saved as csv-file. 
        This does not apply for the imported rois, nor the project configs. 
        """
        self.save_file_infos()
        self.save_project_configs()
        self.save_imported_rois()
    
    
    def save_file_infos(self):
        filepath = f'{self.results_dir}{datetime.now().strftime("%Y_%m_%d")}_findmycells_project_summary.p'
        with open(filepath, 'wb') as io:
            pickle.dump(self.file_infos, io)
            
        
    def save_project_configs(self):
        filepath = f'{self.results_dir}{datetime.now().strftime("%Y_%m_%d")}_findmycells_project_configs.p'
        
        project_configs = dict()
        for key, value in self.__dict__.items():
            if type(value) == str:
                project_configs[key] = value
        
        project_configs['preprocessing'] = dict()
        for key in self.preprocessing_configs.keys():
            project_configs['preprocessing'][key] = self.preprocessing_configs[key].copy()
            project_configs['preprocessing'][key]['method_category'] = project_configs['preprocessing'][key]['ProcessingMethod'].method_category
            project_configs['preprocessing'][key]['method_specifier'] = project_configs['preprocessing'][key]['ProcessingMethod'].method_info
        
        with open(filepath, 'wb') as io:
            pickle.dump(project_configs, io)
                             
    
    def save_imported_rois(self):
        if hasattr(self, 'rois_as_shapely_polygons'):
            filepath = f'{self.results_dir}{datetime.now().strftime("%Y_%m_%d")}_findmycells_imported_rois.p'
            with open(filepath, 'wb') as io:
                pickle.dump(self.rois_as_shapely_polygons, io)
        else:
            pass
                  
    
    def load_all(self):
        result_files = [fname for fname in os.listdir(self.results_dir) if fname.endswith('.p')]
        
        if len(result_files) < 2:
            raise FileNotFoundError(f"Couldn´t find the required files in {self.results_dir}")
        
        else:
            try:
                imported_rois_filename = [fname for fname in result_files if fname.endswith('imported_rois.p')][0]
                with open(self.results_dir + imported_rois_filename, 'rb') as io:
                    self.rois_as_shapely_polygons = pickle.load(io)
            except:
                pass
        
            project_summary_filename = [fname for fname in result_files if fname.endswith('project_summary.p')][0]
            with open(self.results_dir + project_summary_filename, 'rb') as io:
                self.file_infos = pickle.load(io)

            project_configs_filename = [fname for fname in result_files if fname.endswith('project_configs.p')][0]
            with open(self.results_dir + project_configs_filename, 'rb') as io:
                project_configs = pickle.load(io)
            
            self.preprocessing_configs = project_configs['preprocessing'].copy()
            project_configs.pop('preprocessing')
            
            for key, value in project_configs.items():
                if hasattr(self, key) == False:
                    setattr(self, key, value)        
        
    
    
    
    ######################################
    # Deprecated methods - can be deleted?
    def create_subdirectory_structure(self, subdir):
        subjects_per_group = list(set(zip(self.file_infos['group_id'], self.file_infos['subject_id'])))
        for group in set(self.file_infos['group_id']):
            group_dir = subdir + group + '/'
            if os.path.isdir(group_dir) == False:
                os.mkdir(group_dir)
            for subject in [elem[1] for elem in subjects_per_group if elem[0] == group]:
                subject_dir = group_dir + subject + '/'
                if os.path.isdir(subject_dir) == False:
                    os.mkdir(subject_dir)