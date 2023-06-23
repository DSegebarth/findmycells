# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/04_readers_01_microscopy_images.ipynb.

# %% auto 0
__all__ = ['MicroscopyImageReaders', 'CZIReader', 'RegularImageFiletypeReader', 'FromExcelReader']

# %% ../../nbs/api/04_readers_01_microscopy_images.ipynb 2
from abc import abstractmethod
from typing import List, Tuple, Optional, Dict, Any
from pathlib import PosixPath, Path
import numpy as np
import czifile
from skimage.io import imread

from ..core import DataReader, DataLoader

# %% ../../nbs/api/04_readers_01_microscopy_images.ipynb 4
class MicroscopyImageReaders(DataReader):
    """
    The read method of MicroscopyImageReaders subclasses has to return a numpy array with the following structure:
    [imaging-planes, rows, columns, color-channels] 
    For instance, an array of a RGB z-stack with 10 image planes of 1024x1024 pixels will have a shape of:
    [10, 1024, 1024, 3]
    To improve re-usability of the same functions for all different kinds of input images, this structure will 
    be used even if there is just a single plane. For instance, the shape of the array of a grayscale 
    2D image with 1024 x 1024 pixels will look like this:
    [1, 1024, 1024, 1]    
    """

    def assert_correct_output_format(self, output: np.ndarray) -> None:
        assert type(output) == np.ndarray, 'The constructed output is not a numpy array!'
        assert len(output.shape) == 4, 'The shape of the to-be-returned array does not match the expected shape!'
        
        
    def _get_color_channel_slice(self, reader_configs: Dict[str, Any]) -> slice:
        if reader_configs['all_color_channels'] == True:
            color_channel_slice = slice(None)
        else:
            if type(reader_configs['specific_color_channel_idxs_range']) == int:
                lower_color_channel_idx = reader_configs['specific_color_channel_idxs_range']
                upper_color_channel_idx = lower_color_channel_idx
            else:
                lower_color_channel_idx, upper_color_channel_idx = reader_configs['specific_color_channel_idxs_range']
            # To ensure that we are not loosing a dimension when only a single idx shall be selected:
            if lower_color_channel_idx == upper_color_channel_idx:
                upper_color_channel_idx += 1
            color_channel_slice = slice(lower_color_channel_idx, upper_color_channel_idx)
        return color_channel_slice
    
    
    def _get_plane_idx_slice(self, reader_configs: Dict[str, Any]) -> slice:
        if reader_configs['all_planes'] == True:
            plane_idx_slice = slice(None)
        else:
            if type(reader_configs['specific_plane_idxs_range']) == int:
                lower_plane_idx = reader_configs['specific_plane_idxs_range']
                upper_plane_idx = reader_configs['specific_plane_idxs_range']
            else:
                lower_plane_idx, upper_plane_idx = reader_configs['specific_plane_idxs_range']
            # To ensure that we are not loosing a dimension when only a single idx shall be selected:
            if lower_plane_idx == upper_plane_idx:
                upper_plane_idx += 1
            plane_idx_slice = slice(lower_plane_idx, upper_plane_idx)
        return plane_idx_slice

# %% ../../nbs/api/04_readers_01_microscopy_images.ipynb 5
class CZIReader(MicroscopyImageReaders):
    
    """
    This reader enables loading of images acquired with the ZEN imaging software by Zeiss, using the czifile package.
    Note: the first three dimensions are entirely guessed, it could well be that they reflect different things and 
    not "version_idx", "tile_row_idx", "tile_col_idx"!
    """
    
    @property
    def readable_filetype_extensions(self) -> List[str]:
        return ['.czi']
    
    
    def read(self,
             filepath: Path, # filepath to the microscopy image file
             reader_configs: Dict # a dictionary based on the DefaultConfigs specified in the MicroscopyReaderSpecs
            ) -> np.ndarray: # numpy array with the structure: [imaging-planes, rows, columns, imaging-channel]
        color_channel_slice = self._get_color_channel_slice(reader_configs = reader_configs)
        plane_idx_slice = self._get_plane_idx_slice(reader_configs = reader_configs)
        read_image_using_configs = czifile.imread(filepath)[reader_configs['version_idx'],
                                                            reader_configs['tile_row_idx'], 
                                                            reader_configs['tile_col_idx'], 
                                                            plane_idx_slice, 
                                                            :, 
                                                            :, 
                                                            color_channel_slice]
        return read_image_using_configs

# %% ../../nbs/api/04_readers_01_microscopy_images.ipynb 6
class RegularImageFiletypeReader(MicroscopyImageReaders):
    
    """
    This reader enables loading of all regular image filetypes, that scikit-image can read, using the scikit-image.io.imread function.
    Note: So far only single plane images are supported (yet, both single-color & multi-color channel images are supported)!
    """
    
    @property
    def readable_filetype_extensions(self) -> List[str]:
        # ToDo: figure out which formats are possible, probably many many more.. 
        return ['.png', '.tif', '.tiff', '.jpg']
    
    
    def read(self,
             filepath: PosixPath, # filepath to the microscopy image file
             reader_configs: Dict # a dictionary based on the DefaultConfigs specified in the MicroscopyReaderSpecs
            ) -> np.ndarray: # numpy array with the structure: [imaging-planes, rows, columns, imaging-channel]
        image_with_correct_format = self._attempt_to_load_image_at_correct_format(filepath = filepath)
        color_channel_slice = self._get_color_channel_slice(reader_configs = reader_configs)
        read_image_using_configs = image_with_correct_format[:, :, :, color_channel_slice]
        return read_image_using_configs 
    
    
    def _attempt_to_load_image_at_correct_format(self, 
                                                 filepath: PosixPath
                                                ) -> np.ndarray:
        single_plane_image = imread(filepath)
        if len(single_plane_image.shape) == 2: # single color channel
            image_with_correct_format = np.expand_dims(single_plane_image, axis=[0, -1])
        elif len(single_plane_image.shape) == 3: # multiple color channels (at least when assumption of "single plane image" holds)
            image_with_correct_format = np.expand_dims(single_plane_image, axis=[0])
        else:
            raise NotImplementedError('There is something odd with the dimensions of the image you´re attempting to load. '
                                      'It should have either 2 or 3 dimensions, if it is a 2D image with a single color '
                                      'channel, or with multiple color channels, respectively. However, the file you´d like '
                                      f'to load has {len(single_plane_image.shape)} dimensions. For developers: the shape '
                                      f'was: {single_plane_image.shape}.')
        return image_with_correct_format

# %% ../../nbs/api/04_readers_01_microscopy_images.ipynb 7
class FromExcelReader(MicroscopyImageReaders):
    
    """
    This reader is actually only a wrapper to the other MicroscopyImageReaders subclasses. It can be used if you stored the filepaths
    to your individual plane images in an excel sheet, for instance if you were using our "prepare my data for findmycells" functions.
    Please be aware that the corresponding datatype has to be loadable with any of the corresponding MicroscopyImageReaders!
    """
    
    @property
    def readable_filetype_extensions(self) -> List[str]:
        # ToDo: figure out which formats are possible, probably many many more.. 
        return ['.xlsx']
        
    
    def read(self,
             filepath: PosixPath, # filepath to the excel sheet that contains the filepaths to the corresponding image files
             reader_configs: Dict # a dictionary based on the DefaultConfigs specified in the MicroscopyReaderSpecs
            ) -> np.ndarray: # numpy array with the structure: [imaging-planes, rows, columns, imaging-channel]

        import findmycells.readers as readers
        
        df_single_plane_filepaths = pd.read_excel(filepath)
        single_plane_images = []
        for row_index in range(df_single_plane_filepaths.shape[0]):
            single_plane_image_filepath = Path(df_single_plane_filepaths['plane_filepath'].iloc[row_index])
            file_extension = single_plane_image_filepath.suffix
            image_loader = DataLoader()
            image_reader_class = image_loader.determine_reader(file_extension = file_extension,
                                                               data_reader_module = readers.microscopy_images)
            loaded_image = image_loader.load(data_reader_class = image_reader_class,
                                             filepath = single_plane_image_filepath,
                                             reader_configs = reader_configs)
            single_plane_images.append(loaded_image)
        read_image_using_configs = np.stack(single_plane_images)
        return read_image_using_configs
