# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/03_api.ipynb.

# %% auto 0
__all__ = ['API']

# %% ../nbs/03_api.ipynb 2
from pathlib import Path, PosixPath
from typing import List, Dict, Tuple, Optional, Union

from tqdm.notebook import tqdm
from datetime import datetime
import pickle

from .configs import ProjectConfigs
from .database import Database
from .core import ProcessingStrategy
from .preprocessing.specs import PreprocessingStrategy, PreprocessingObject

# %% ../nbs/03_api.ipynb 4
class API:
    
    def __init__(self, project_root_dir: PosixPath) -> None:
        assert type(project_root_dir) == PosixPath, '"project_root_dir" must be pathlib.Path object referring to an existing directory.'
        assert project_root_dir.is_dir(), '"project_root_dir" must be pathlib.Path object referring to an existing directory.'
        self.project_configs = ProjectConfigs(root_dir = project_root_dir)
        self.database = Database(project_configs = self.project_configs)
        
        
    def update_database_with_current_source_files(self, skip_checking: bool=False) -> None:
        self.database.compute_file_infos(skip_checking = skip_checking)
        
        
    def preprocess(self,
                   strategies: List[PreprocessingStrategy],
                   strategy_configs: Optional[List[Dict]]=None,
                   processing_configs: Optional[Dict]=None,
                   microscopy_reader_configs: Optional[Dict]=None,
                   roi_reader_configs: Optional[Dict]=None,
                   file_ids: Optional[List[str]]=None
                  ) -> None:
        processing_step_id = 'preprocessing'
        strategy_configs, processing_configs, file_ids = self._assert_and_update_input(processing_step_id = processing_step_id,
                                                                                       strategies = strategies,
                                                                                       strategy_configs = strategy_configs,
                                                                                       processing_configs = processing_configs,
                                                                                       file_ids = file_ids)
        microscopy_reader_configs = self._assert_and_update_reader_configs_input(reader_type = 'microscopy_images', reader_configs = microscopy_reader_configs)
        roi_reader_configs = self._assert_and_update_reader_configs_input(reader_type = 'rois', reader_configs = roi_reader_configs)
        for file_id in tqdm(file_ids, display = processing_configs['show_progress']):
            preprocessing_object = PreprocessingObject()
            preprocessing_object.prepare_for_processing(file_ids = [file_id], database = self.database)
            preprocessing_object.load_image_and_rois(microscopy_reader_configs = microscopy_reader_configs, roi_reader_configs = roi_reader_configs)
            preprocessing_object.run_all_strategies(strategies = strategies, strategy_configs = strategy_configs)
            preprocessing_object.save_preprocessed_images_on_disk()
            preprocessing_object.save_preprocessed_rois_in_database()
            preprocessing_object.update_database()
            del preprocessing_object
            if processing_configs['autosave'] == True:
                self.save_status()
                self.load_status()
                
                
    def _assert_and_update_reader_configs_input(self, reader_type: str, reader_configs: Optional[Dict]) -> Dict:            
        if reader_configs == None:
            if hasattr(self.project_configs, reader_type) == False:
                self.project_configs.add_reader_configs(reader_type = reader_type)
            reader_configs = getattr(self.project_configs, reader_type)
        else:
            assert type(reader_configs) == dict, f'"reader_configs" (data type: {reader_type}) has to be a dictionary!'
            default_configs = self.project_configs.default_configs_of_available_data_readers[reader_type]
            default_configs.assert_user_input(user_input = reader_configs)
            reader_configs = default_configs.fill_user_input_with_defaults_where_needed(user_input = reader_configs)
            self.project_configs.add_reader_configs(reader_type = reader_type, reader_configs = reader_configs)
        return reader_configs

    
    def save_status(self) -> None:
        date = f'{datetime.now():%Y_%m_%d}'
        dbase_filename = f'{date}_findmycells_database.dbase'
        self._save_attr_to_disk(attr_id = 'database', filename = dbase_filename, child_attr_ids_to_del = ['project_configs'])
        configs_filename = f'{date}_findmycells_project.configs'
        self._save_attr_to_disk(attr_id = 'project_configs', filename = configs_filename, child_attr_ids_to_del = ['available_processing_modules'])
        
    
    def _save_attr_to_disk(self, attr_id: str, filename: str, child_attr_ids_to_del: List[str]) -> None:
        filepath = self.project_configs.root_dir.joinpath(filename)
        attribute_to_save = getattr(self, attr_id)
        for attr_id_to_del in child_attr_ids_to_del:
            delattr(attribute_to_save, attr_id_to_del)
        filehandler = open(filepath, 'wb')
        pickle.dump(attribute_to_save, filehandler)

        
    def _load_object_from_filepath(self, filepath: PosixPath) -> Union[Database, ProjectConfigs]:
        filehandler = open(filepath, 'rb')
        loaded_object = pickle.load(filehandler)
        return loaded_object

        
    def load_status(self,
                    project_configs_filepath: Optional[PosixPath]=None,
                    database_filepath: Optional[PosixPath]=None
                   ) -> None:
        if project_configs_filepath != None:
            assert type(project_configs_filepath) == PosixPath, '"project_configs_filepath" must be pathlib.Path object referring to a .configs file.'
            assert project_configs_filepath.suffix == '.configs', '"project_configs_filepath" must be pathlib.Path object referring to a .configs file.'
        else:
            project_configs_filepath = self._look_for_latest_status_file_in_dir(suffix = '.configs', dir_path = self.project_configs.root_dir)
        if database_filepath != None:
            assert type(database_filepath) == PosixPath, '"database_filepath" must be pathlib.Path object referring to a .dbase file'
            assert database_filepath.suffix == '.dbase', '"database_filepath" must be pathlib.Path object referring to a .dbase file'
        else:
            database_filepath = self._look_for_latest_status_file_in_dir(suffix = '.dbase', dir_path = self.project_configs.root_dir)
        if hasattr(self, 'project_configs'):
            delattr(self, 'project_configs')
        if hasattr(self, 'database'):
            delattr(self, 'database')
        self.project_configs = self._load_object_from_filepath(filepath = project_configs_filepath)
        self.project_configs.load_available_processing_modules()
        self.database = self._load_object_from_filepath(filepath = database_filepath)
        setattr(self.database, 'project_configs', self.project_configs)
        

    def split_file_ids_into_batches(self, file_ids: List[str], batch_size: int) -> List[List[str]]:
        if len(file_ids) % batch_size == 0:
            total_batches = int(len(file_ids) / batch_size)
        else:
            total_batches = int(len(file_ids) / batch_size) + 1
        file_ids_per_batch = []
        for batch in range(total_batches):
            if len(file_ids) >= batch_size:
                sampled_file_ids = random.sample(file_ids, batch_size)
            else:
                sampled_file_ids = file_ids.copy()
            file_ids_per_batch.append(sampled_file_ids)
            for elem in sampled_file_ids:
                file_ids.remove(elem)    
        return file_ids_per_batch


    def _look_for_latest_status_file_in_dir(self, suffix: str, dir_path: PosixPath) -> PosixPath:
        matching_filepaths = [filepath for filepath in dir_path.iterdir() if filepath.suffix == suffix]
        if len(matching_filepaths) == 0:
            raise FileNotFoundError(f'Could not find a "{suffix}" file in {dir_path}. Consider specifying the exact filepath!')
        else:
            date_strings = [filepath.name[:10] for filepath in matching_filepaths]
            dates = [datetime.strptime(date_str, '%Y_%m_%d') for date_str in date_strings]
            latest_date = max(dates)
            filepath_idx = dates.index(latest_date)
            latest_status_filepath = matching_filepaths[filepath_idx]
        return latest_status_filepath        
        
        
    def _assert_and_update_input(self, 
                                 processing_step_id: str,
                                 strategies: List[PreprocessingStrategy],
                                 strategy_configs: Optional[List[Dict]],
                                 processing_configs: Optional[Dict],
                                 file_ids: Optional[List[str]]
                                ) -> Tuple[List[Dict], Dict, List[str]]:
        self._assert_processing_step_input(processing_step_id = processing_step_id,
                                           strategies = strategies,
                                           strategy_configs = strategy_configs,
                                           processing_configs = processing_configs,
                                           file_ids = file_ids)
        strategy_configs = self._fill_strategy_configs_with_defaults_where_needed(strategies, strategy_configs)
        if processing_configs == None:
            if hasattr(self.project_configs, processing_step_id) == False:
                self.project_configs.add_processing_step_configs(processing_step_id = processing_step_id)
            processing_configs = getattr(self.project_configs, processing_step_id)
        processing_configs = self._fill_processing_configs_with_defaults_where_needed(processing_step_id, processing_configs)
        self.project_configs.add_processing_step_configs(processing_step_id, configs = processing_configs)
        file_ids = self.database.get_file_ids_to_process(input_file_ids = file_ids,
                                                         processing_step_id = processing_step_id,
                                                         overwrite = processing_configs['overwrite'])
        return strategy_configs, processing_configs, file_ids
            
        
    def _assert_processing_step_input(self, 
                                      processing_step_id: str,
                                      strategies: List[PreprocessingStrategy],
                                      strategy_configs: Optional[List[Dict]],
                                      processing_configs: Optional[Dict],
                                      file_ids: Optional[List[str]]
                                     ) -> None:
        assert type(strategies) == list, '"strategies" has to ba a list of ProcessingStrategy classes of the respective processing step!'
        if strategy_configs != None:
            assert type(strategy_configs) == list, '"strategy_configs" has to be None or a list of the same length as "strategies"!'
            assert len(strategy_configs) == len(strategies), '"strategy_configs" has to be None or a list of the same length as "strategies"!'
        else:
            strategy_configs = [None] * len(strategies)
        available_strategies = self.project_configs.available_processing_strategies[processing_step_id]
        for strat, config in zip(strategies, strategy_configs):
            assert strat in available_strategies, f'{strat} is not an available strategy for {processing_step_id}!'
            if config != None:
                strat().default_configs.assert_user_input(user_input = config)
        if processing_configs != None:
            processing_obj = self.project_configs.available_processing_objects[processing_step_id]()
            processing_obj.default_configs.assert_user_input(user_input = processing_configs)
        if file_ids != None:
            assert type(file_ids) == list, '"file_ids" has to be a list of strings referring to file_ids in the database!'
            for elem in file_ids:
                assert elem in self.database.file_infos['file_id'], f'{elem} is not a valid file_id!'
        
        
    def _fill_processing_configs_with_defaults_where_needed(self,
                                                            processing_step_id: str,
                                                            processing_configs: Dict
                                                           ) -> Dict:
        processing_obj = self.project_configs.available_processing_objects[processing_step_id]()
        return processing_obj.default_configs.fill_user_input_with_defaults_where_needed(user_input = processing_configs)                                              
             
        
    def _fill_strategy_configs_with_defaults_where_needed(self,
                                                          strategies: List[ProcessingStrategy],
                                                          strategy_configs: Optional[List[Dict]]
                                                         ) -> List[Dict]:
        all_final_configs = []
        if strategy_configs == None:
            for strat in strategies:
                default_configs = strat().default_configs.fill_user_input_with_defaults_where_needed(user_input = {})
                all_final_configs.append(default_configs)
        else:
            for strat, configs in zip(strategies, strategy_configs):
                full_configs = strat().default_configs.fill_user_input_with_defaults_where_needed(user_input = configs)
                all_final_configs.append(full_configs)
        return all_final_configs
