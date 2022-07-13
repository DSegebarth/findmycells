from abc import ABC, abstractmethod
from .database import Database
from typing import List, Dict


class ProcessingObject(ABC):
    
    def __init__(self, database: Database, file_ids: List, strategies: List) -> None:
        self.database = database
        self.file_ids = file_ids
        self.strategies = strategies # strategies is a list of ProcessingStrategies (can of course also be just a single strategy)
        # additional attributes can be added in the respective subclasses


    def run_all_strategies(self) -> None:
        for strategy in self.strategies:
            processing_strategy = strategy()
            self = processing_strategy.run(processing_object = self)
            self = processing_strategy.update_database(processing_object = self)
            del processing_strategy


    def update_database(self) -> None:
        for file_id in self.file_ids:
            updates = dict()
            updates[f'{self.processing_type}_completed'] = True
            updates = self.add_processing_specific_infos_to_updates(updates = updates)
            self.database.update_file_infos(file_id = file_id, updates = updates)


    @property
    @abstractmethod
    def processing_type(self):
        # has to be any of these: 'preprocessing', 'segmentation', 'quantification', 'inspection'
        pass


    @abstractmethod
    def add_processing_specific_infos_to_updates(self, updates: Dict) -> Dict:
        # add all additional ProcessingObject specifc information to the update dictionary,
        # which is not already covered in the individual ProcessingStrategies.
        # Or simply return updates right away if there are no information to add
        return updates



class ProcessingStrategy(ABC):
    
    @property
    def strategy_name(self):
        return self.__class__.__name__ 


    def update_database(self, processing_object: ProcessingObject) -> ProcessingObject:
        for file_id in processing_object.file_ids:
            updates = dict()
            step_index = self.determine_correct_step_index(database = processing_object.database, file_id = file_id)
            updates[f'{self.processing_type}_step_{str(step_index).zfill(2)}'] = self.strategy_name
            updates = self.add_strategy_specific_infos_to_updates(updates = updates)
            processing_object.database.update_file_infos(file_id = file_id, updates = updates)
        return processing_object
            
    
    def determine_correct_step_index(self, database: Database, file_id: str) -> int:
        file_infos = database.get_file_infos(identifier = file_id)
        previous_step_indices_of_same_processing_type = []
        for key, value in file_infos.items():
            if f'{self.processing_type}_step_' in key:
                if value != None: # to ensure that this file_id was actually already processed
                    step_index = int(key[key.rfind('_') + 1 :])
                    previous_step_indices_of_same_processing_type.append(step_index)
        if len(previous_step_indices_of_same_processing_type) > 0:
            correct_step_index = max(previous_step_indices_of_same_processing_type) + 1
        else:
            correct_step_index = 0
        return correct_step_index


    @property
    @abstractmethod
    def processing_type(self):
        # has to be any of these: 'preprocessing', 'segmentation', 'quantification', 'inspection'
        pass


    @abstractmethod
    def run(self, processing_object: ProcessingObject) -> ProcessingObject:
        # process the processing_object
        return processing_object

    
    @abstractmethod
    def add_strategy_specific_infos_to_updates(self, updates: Dict) -> Dict:
        # add all ProcessingStrategy specifc information to the update dictionary
        # or simply return updates right away if there are no information to add
        return updates
    
