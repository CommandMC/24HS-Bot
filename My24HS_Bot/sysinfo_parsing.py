import logging

from discord import Embed

from My24HS_Bot.const import w10_build_to_version, w11_build_to_version, latest_nvidia_version, embed_color, \
    latest_amd_version


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

    def windows_version(self, os_name: str, windows_build: str):
        if os_name.startswith('Microsoft Windows 10'):
            is_up_to_date, current_version, latest_version = build_version_check(windows_build, w10_build_to_version)
        elif os_name.startswith('Microsoft Windows 11'):
            is_up_to_date, current_version, latest_version = build_version_check(windows_build, w11_build_to_version)
            current_version = '**W11**-' + current_version
        else:
            is_up_to_date = False
            current_version = 'Unsupported, W7?'

        if not is_up_to_date:
            self.add_info('Windows version', ':x: Not up to date ({})'.format(current_version))
            self.quickfixes.description += '`/systemuptodate`\n - Update Windows\n'
            self.logger.info('Windows version {}, not up to date'.format(current_version))
            return
        self.add_info('Windows version', ':white_check_mark: Up to date ({})'.format(current_version))
        self.logger.info('Windows version {}, up to date'.format(current_version))

    def ram_capacity(self, ram_capacity: str) -> int:
        ram_capacity = ram_capacity.replace(',', '.')
        ram_capacity_gb = int(ram_capacity.split('.')[0])
        self.logger.info('RAM Capacity: {} GB'.format(ram_capacity_gb))
        if ram_capacity_gb < 8:
            self.add_info('RAM Capacity', ':warning: {} GB'.format(ram_capacity_gb))
        else:
            self.add_info('RAM Capacity', ':white_check_mark: {} GB'.format(ram_capacity_gb))
        return ram_capacity_gb

    def add_gpus(self, gpunames, gpuversions):
        # This determines where and when we have to insert blank fields
        magic_formatting_num = len(self.info.fields) % 3
        for i in range(len(gpunames)):
            # If we started with having one field until a new row, add an empty field now
            if magic_formatting_num == 2:
                self.add_info('\u200b', '\u200b')
                magic_formatting_num = 0
            gpuname = gpunames[i]
            self.add_info('GPU {}'.format(i + 1) if len(gpunames) != 1 else 'GPU', gpuname)

            gpu_outdated = False
            # GPU driver update checking is currently only possible on NVIDIA GPUs
            if gpuname.startswith('NVIDIA'):
                if gpuversions[i] == latest_nvidia_version:
                    gpu_ver_string = ':white_check_mark: Up to date ({})'.format(gpuversions[i])
                else:
                    gpu_ver_string = ':x: Not up to date ({})'.format(gpuversions[i])
                    gpu_outdated = True
            elif gpuname.startswith('AMD'):
                if gpuversions[i] == latest_amd_version:
                    gpu_ver_string = ':white_check_mark: Up to date ({})'.format(gpuversions[i])
                else:
                    gpu_ver_string = ':x: Not up to date ({})'.format(gpuversions[i])
                    gpu_outdated = True
            else:
                gpu_ver_string = gpuversions[i]

            self.add_info('Driver Version', gpu_ver_string)

            # If we started with 2 fields to spare, the first GPU doesn't need a blank field
            if magic_formatting_num == 1:
                magic_formatting_num = 0
            # And finally, if we're on our last GPU, there's no need to add an empty field
            elif i != len(gpunames) - 1:
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


def build_version_check(build_num: str, build_to_version: dict) -> tuple[bool, str, str]:
    if build_num not in build_to_version:
        raise ValueError('The build number supplied ({}) does not exist'.format(build_num))
    version_name: str = build_to_version[build_num]
    latest_version_build = list(build_to_version.keys())[-1]
    if build_num == latest_version_build:
        # If the latest build number and the supplied build number match, we can just
        # return the current version name as the most recent
        return True, version_name, version_name
    return False, version_name, list(build_to_version.values())[-1]
