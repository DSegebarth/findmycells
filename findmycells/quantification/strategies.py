# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/08_quantification_01_strategies.ipynb.

# %% auto 0
__all__ = ['CountFeaturesInWholeAreaROIs']

# %% ../../nbs/08_quantification_01_strategies.ipynb 2
from typing import Tuple, List, Dict
from pathlib import Path

import cc3d

from .specs import QuantificationObject, QuantificationStrategy
from ..database import Database
from .. import utils

# %% ../../nbs/08_quantification_01_strategies.ipynb 4
class CountFeaturesInWholeAreaROIs(QuantificationStrategy):
    
    
    def run(self, processing_object: QuantificationObject) -> QuantificationObject:
        print('-counting the number of image features per region of interest')
        quantification_results = {}
        for area_roi_id in processing_object.segmentations_per_area_roi_id.keys():
            _, feature_count = cc3d.connected_components(processing_object.segmentations_per_area_roi_id[area_roi_id], return_N=True)
            quantification_results[area_roi_id] = feature_count
        processing_object = self._add_quantification_results_to_database(quantification_object = processing_object, results = quantification_results)
        return processing_object


    def _add_quantification_results_to_database(self, quantification_object: QuantificationObject, results: Dict) -> QuantificationObject:
        if hasattr(quantification_object.database, 'quantification_results') == False:
            setattr(quantification_object.database, 'quantification_results', {})
        if self.__class__.__name__ not in quantification_object.database.quantification_results.keys():
            quantification_object.database.quantification_results[self.__class__.__name__] = {}
        quantification_object.database.quantification_results[self.__class__.__name__][quantification_object.file_id] = results
        return quantification_object


    def add_strategy_specific_infos_to_updates(self, updates: Dict) -> Dict:
        return updates
