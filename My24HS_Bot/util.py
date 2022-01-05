from io import StringIO, BytesIO
from typing import Union

from discord import Embed, Attachment

from My24HS_Bot.const import system_manufacturer_unknown_values, system_model_unknown_values, nvidia_driver_versions, \
    amd_driver_versions
from My24HS_Bot.sysinfo_parsing import SysinfoParser


def go_to_section(fd: StringIO, section: int):
    fd.seek(0)
    i = 0
    while i < section:
        curr_line = fd.readline()
        if curr_line.startswith('['):
            i += 1
    for i in range(2):
        fd.readline()


def convert_utf16_utf8(fd: BytesIO) -> StringIO:
    utf8 = StringIO()
    utf8.writelines(fd.read().decode('utf-16'))
    utf8.seek(0)
    return utf8


def is_sysinfo(fd: StringIO) -> bool:
    # The 6th line of a sysinfo file contains the OS name.
    # The "Value" portion of that should always start with "Microsoft Windows 10", so that's what we're using
    # to detect if this is actually a sysinfo file

    # Discard the first 5 lines
    for i in range(5):
        fd.readline()
    # Read out the 6th line
    os_name_line = fd.readline()
    fd.seek(0)
    try:
        os_name = os_name_line.split('\t')[1].replace('\u200f', '')
    # If we don't have a 2nd element (-> no tabs in line), we also know this can't be a sysinfo file
    except IndexError:
        return False
    return os_name.startswith('Microsoft Windows 1')


def handle_sysinfo(fd: StringIO) -> tuple[Embed, Embed]:
    parser = SysinfoParser()

    for i in range(5):
        fd.readline()
    os_name = fd.readline().split('\t')[1]
    windows_version = fd.readline().split('\t')[1]
    windows_build = windows_version.split(' ')[-1]
    parser.windows_version(os_name, int(windows_build))

    for i in range(3):
        fd.readline()
    system_manufacturer = fd.readline().split('\t')[1]
    system_manufacturer_unknown = system_manufacturer in system_manufacturer_unknown_values
    if not system_manufacturer_unknown:
        parser.add_info('System Manufacturer', system_manufacturer)
    system_model = fd.readline().split('\t')[1]
    system_model_unknown = system_model in system_model_unknown_values
    if not system_model_unknown:
        parser.add_info('System Model', system_model)

    for i in range(2):
        fd.readline()
    processor = fd.readline().split('\t')[1].split(',')[0]
    bios_info = fd.readline().split('\t')[1]
    # Don't add them yet, they'll be added once BaseBoard is read out
    if not (system_manufacturer_unknown or system_model_unknown):
        parser.add_info('Processor', processor)
        parser.add_info('BIOS Version & Date', bios_info)

    for i in range(3):
        fd.readline()
    # If the System Manufacturer or the System Model is deemed unknown/unhelpful, try to read out BaseBoard instead
    baseboard_manufacturer_line = fd.readline()
    if system_manufacturer_unknown or system_model_unknown:
        if system_manufacturer_unknown:
            baseboard_manufacturer = baseboard_manufacturer_line.split('\t')[1]
            parser.add_info('System Manufacturer', baseboard_manufacturer)
        if system_model_unknown:
            baseboard_product = fd.readline().split('\t')[1]
            parser.add_info('System Model', baseboard_product)
        else:
            fd.readline()
        # Skip "BaseBoard-Version" and "Platform Role"
        for i in range(2):
            fd.readline()
        # And now we add the CPU and BIOS info
        parser.add_info('Processor', processor)
        parser.add_info('BIOS Version & Date', bios_info)
    else:
        for i in range(3):
            fd.readline()

    # At this point, we should be at "Secure Boot State"

    for i in range(9):
        fd.readline()
    ram_capacity = fd.readline().split('\t')[1]
    parser.ram_capacity(ram_capacity)

    for i in range(8):
        fd.readline()
    # If TPM is in here, there was an error with it, so it's not supported
    tpm_available = 'TPM' not in fd.readline().split('\t')[1]
    parser.logger.info('TPM is {}supported'.format('' if tpm_available else 'not '))

    tpm_version = 'Unknown'
    if tpm_available:
        # Go to [Memory]
        go_to_section(fd, 8)
        for line in fd:
            try:
                device = line.split('\t')[1]
            except IndexError:
                # If we haven't found the TPM version info in there, it isn't loaded and thus not available
                # This usually indicates some other problem earlier on (maybe some lines are missing in the system
                # summary section), but once we 'go_to_section' we should be able to ignore them
                tpm_available = False
                break
            if device.startswith('Trusted Platform Module'):
                tpm_version = device.split(' ')[-1]
                break
    parser.add_info('TPM Version', ':white_check_mark: ' + tpm_version if tpm_available else ':x: Not supported')

    # Go to [Display]
    go_to_section(fd, 15)

    # We're accounting for multi-GPU systems by creating lists here
    gpunames: list[str] = []
    gpuversions: list[str] = []
    gpu_done = False
    while not gpu_done:
        gpunames.append(fd.readline().split('\t')[1])
        for i in range(5):
            fd.readline()
        gpu_driver_version = fd.readline().split('\t')[1]
        # For NVIDIA GPUs, we can format the version string properly and later check if the driver is up to date
        if gpunames[-1].startswith('NVIDIA'):
            gpu_driver_version = gpu_driver_version.replace('.', '')[-5:]
            gpu_driver_version = gpu_driver_version[0:3] + '.' + gpu_driver_version[3:]
        gpuversions.append(gpu_driver_version)
        for line in fd:
            # Two tabs are used to indicate that there's another GPU installed.
            # If that's the case, run the while-Loop again to add the next GPU
            if line.startswith('\t\t'):
                break
            # If [ is encountered, the next section was reached. If that's the case, we're done with listing GPUs
            if line.startswith('['):
                gpu_done = True
                break

    # Add all detected GPUs to the system info embed
    parser.add_gpus(gpunames, gpuversions)

    fd.seek(0)
    return parser.info, parser.quickfixes


async def download_sysinfo(attachment: Attachment) -> Union[StringIO, bool]:
    storage = BytesIO()
    await attachment.save(storage)
    utf8_sysinfo = convert_utf16_utf8(storage)
    if not is_sysinfo(utf8_sysinfo):
        return False
    return utf8_sysinfo
