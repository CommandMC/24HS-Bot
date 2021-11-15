import logging
from dataclasses import dataclass

from discord import Embed

from My24HS_Bot.const import w10_build_to_version, w11_build_to_version, embed_color, nvidia_driver_versions, \
    amd_driver_versions


@dataclass
class WinVerInfo:
    is_up_to_date: bool = False
    current_version_name: str = ''
    latest_version_name: str = ''
    is_insider: bool = False


class SysinfoParser:
    def __init__(self):
        self.info = Embed(
            title=':information_source: System Information',
            colour=embed_color
        )
        self.quickfixes = Embed(
            title=':tools: Quick Fixes',
            colour=embed_color,
            description=''
        )
        self.logger = logging.getLogger('SysinfoParser')

    def windows_version(self, os_name: str, windows_build: int):
        try:
            if os_name.startswith('Microsoft Windows 11'):
                ver_info = build_version_check(windows_build, w11_build_to_version)
                ver_info.current_version_name = '**W11**-' + ver_info.current_version_name
            else:
                ver_info = build_version_check(windows_build, w10_build_to_version)
        except ValueError:
            self.add_info('Windows version', f':question: Unsure (Build {windows_build})')
            return

        if not ver_info.is_up_to_date:
            self.add_info('Windows version', f':x: Not up to date ({ver_info.current_version_name})')
            self.quickfixes.description += '`/systemuptodate`\n - Update Windows\n'
            self.logger.info(f'Windows version {ver_info.current_version_name}, not up to date')
            return

        if ver_info.is_insider:
            self.add_info('Windows version', f':exclamation: Insider build? (Build {windows_build})')
            return

        self.add_info('Windows version', f':white_check_mark: Up to date ({ver_info.current_version_name})')
        self.logger.info(f'Windows version {ver_info.current_version_name}, up to date')

    def ram_capacity(self, ram_capacity: str) -> int:
        ram_capacity = ram_capacity.replace(',', '.')
        ram_capacity_gb = int(ram_capacity.split('.')[0])
        self.logger.info('RAM Capacity: {} GB'.format(ram_capacity_gb))
        if ram_capacity_gb < 8:
            self.add_info('RAM Capacity', ':warning: {} GB'.format(ram_capacity_gb))
        else:
            self.add_info('RAM Capacity', ':white_check_mark: {} GB'.format(ram_capacity_gb))
        return ram_capacity_gb

    def add_gpus(self, gpu_names, gpu_versions):
        # This determines where and when we have to insert blank fields
        magic_formatting_num = len(self.info.fields) % 3
        for i in range(len(gpu_names)):
            # If we started with having one field until a new row, add an empty field now
            if magic_formatting_num == 2:
                self.add_info('\u200b', '\u200b')
                magic_formatting_num = 0
            gpuname = gpu_names[i]
            self.add_info('GPU {}'.format(i + 1) if len(gpu_names) != 1 else 'GPU', gpuname)

            gpu_outdated = False
            if gpuname.startswith('NVIDIA'):
                if is_up_to_date_nvidia(gpuname, gpu_versions[i]):
                    gpu_ver_string = ':white_check_mark: Up to date ({})'.format(gpu_versions[i])
                else:
                    gpu_ver_string = ':x: Not up to date ({})'.format(gpu_versions[i])
                    gpu_outdated = True
            elif gpuname.startswith('AMD'):
                if is_up_to_date_amd(gpu_versions[i]):
                    gpu_ver_string = ':white_check_mark: Up to date ({})'.format(gpu_versions[i])
                else:
                    gpu_ver_string = ':x: Not up to date ({})'.format(gpu_versions[i])
                    gpu_outdated = True
            else:
                gpu_ver_string = gpu_versions[i]

            self.add_info('Driver Version', gpu_ver_string)

            # If we started with 2 fields to spare, the first GPU doesn't need a blank field
            if magic_formatting_num == 1:
                magic_formatting_num = 0
            # And finally, if we're on our last GPU, there's no need to add an empty field
            elif i != len(gpu_names) - 1:
                # Add an empty 3rd field, since otherwise the ordering would look weird with more than one GPU installed
                self.add_info('\u200b', '\u200b')

            # If the GPU driver we're currently looking at is outdated and the
            # update notice is not yet in the quick fixes, add it
            if gpu_outdated and ' - Update GPU drivers' not in self.quickfixes.description:
                if '`/systemuptodate`' not in self.quickfixes.description:
                    self.quickfixes.description += '`/systemuptodate`\n'
                self.quickfixes.description += ' - Update GPU drivers\n'
            self.logger.info('Added GPU {}, driver version {}, up to date? {}'.format(
                gpuname, gpu_ver_string, gpu_outdated
            ))

    def add_info(self, name: str, value: str):
        self.logger.debug('Adding info {}, value {}'.format(name, value))
        self.info.add_field(name=name, value=value)


def build_version_check(build_num: int, build_to_version_name: dict) -> WinVerInfo:
    ver_info = WinVerInfo()
    latest_version_build = list(build_to_version_name.keys())[-1]
    ver_info.latest_version_name = list(build_to_version_name.values())[-1]

    if build_num not in build_to_version_name:
        # If the build number is smaller than the latest build, we know it can't exist
        if build_num < latest_version_build:
            raise ValueError('The build number supplied ({}) does not exist'.format(build_num))
        # If it's greater, it's probably an insider build
        else:
            ver_info.is_insider = True
            ver_info.is_up_to_date = True
    # If the build number is in the dict
    else:
        # Get the version name
        ver_info.current_version_name = build_to_version_name[build_num]
        # Check if it's up to date
        ver_info.is_up_to_date = build_num == latest_version_build
    return ver_info


def is_up_to_date_nvidia(gpu_name: str, driver_version: str) -> bool:
    branches = nvidia_driver_versions.copy()

    # The professional driver is only an option if you're using a professional GPU
    if not any(name in gpu_name for name in ['Quadro', 'Tesla', 'Grid', 'NVS']):
        branches.pop('professional')

    return any(version == driver_version for version in branches.values())


def is_up_to_date_amd(driver_version: str) -> bool:
    return any(version == driver_version for version in amd_driver_versions.values())
