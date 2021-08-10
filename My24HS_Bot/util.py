from io import StringIO, BytesIO

from discord import Embed

from My24HS_Bot.const import w10_build_to_version, latest_nvidia_version, embed_color


def w10_build_version_check(build_num: str) -> tuple[bool, str, str]:
    if build_num not in w10_build_to_version:
        raise ValueError('The build number supplied ({}) does not exist'.format(build_num))
    version_name: str = w10_build_to_version[build_num]
    latest_version_build = list(w10_build_to_version.keys())[-1]
    if build_num == latest_version_build:
        # If the latest build number and the supplied build number match, we can just
        # return the current version name as the most recent
        return True, version_name, version_name
    return False, version_name, list(w10_build_to_version.values())[-1]


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
    for _ in range(5):
        fd.readline()
    # Read out the 6th line
    os_name_line = fd.readline()
    fd.seek(0)
    try:
        os_name = os_name_line.split('\t')[1]
    # If we don't have a 2nd element (-> no tabs in line), we also know this can't be a sysinfo file
    except IndexError:
        return False
    return os_name.startswith('Microsoft Windows 1')


def parse_sysinfo(fd: StringIO) -> tuple[Embed, Embed]:
    info = Embed(
        title=':information_source: System Information',
        colour=embed_color
    )
    quickfixes = Embed(
        title=':tools: Quick Fixes',
        colour=embed_color,
        description=''
    )

    for _ in range(6):
        fd.readline()

    windows_version = fd.readline().split('\t')[1]
    windows_build = windows_version.split(' ')[-1]
    try:
        is_up_to_date, current_version, latest_version = w10_build_version_check(windows_build)
    except ValueError:
        is_up_to_date = True
        current_version = 'Unknown'
    if not is_up_to_date:
        info.add_field(
            name='Windows version',
            value=':x: Not up to date ({})'.format(current_version)
        )
        quickfixes.description += '`/systemuptodate`\n - Update Windows\n'
    else:
        info.add_field(
            name='Windows version',
            value=':white_check_mark: Up to date ({})'.format(current_version)
        )

    for _ in range(3):
        fd.readline()
    system_manufacturer = fd.readline().split('\t')[1]
    if system_manufacturer == 'To Be Filled By O.E.M.':
        system_manufacturer = 'Unknown'
    info.add_field(
        name='System Manufacturer',
        value=system_manufacturer
    )
    system_model = fd.readline().split('\t')[1]
    if system_model == 'To Be Filled By O.E.M.':
        system_model = 'Unknown'
    info.add_field(
        name='System Model',
        value=system_model
    )

    for _ in range(2):
        fd.readline()
    processor = fd.readline().split('\t')[1].split(',')[0]
    info.add_field(
        name='Processor',
        value=processor
    )

    bios_info = fd.readline().split('\t')[1]
    info.add_field(
        name='BIOS Version & Date',
        value=bios_info
    )

    for _ in range(16):
        fd.readline()
    ram_capacity = fd.readline().split('\t')[1]
    info.add_field(
        name='RAM Capacity',
        value=ram_capacity
    )

    # Skip to the "[Display]" section of the sysinfo by counting how many sections we pass
    i = 0
    while i < 14:
        curr_line = fd.readline()
        if curr_line.startswith('['):
            i += 1
    for _ in range(2):
        fd.readline()
    # We're accounting for multi-GPU systems by creating lists here
    gpunames: list[str] = []
    gpuversions: list[str] = []
    while True:
        gpunames.append(fd.readline().split('\t')[1])
        for i in range(5):
            fd.readline()
        gpu_driver_version = fd.readline().split('\t')[1]
        # For NVIDIA GPUs, we can format the version string properly and later check if the driver is up to date
        if gpunames[-1].startswith('NVIDIA'):
            gpu_driver_version = gpu_driver_version.replace('.', '')[-5:]
            gpu_driver_version = gpu_driver_version[0:3] + '.' + gpu_driver_version[3:]
        gpuversions.append(gpu_driver_version)
        for i in range(10):
            fd.readline()
        if not fd.readline().startswith('\t\t'):
            break

    # Add all detected GPUs to the system info embed
    for i in range(len(gpunames)):
        gpuname = gpunames[i]
        info.add_field(
            # If we only have one GPU to display, it would be redundant to add a " 1" behind it
            name='GPU {}'.format(i + 1) if len(gpunames) != 1 else 'GPU',
            value=gpuname
        )

        gpu_outdated = False
        # GPU driver update checking is currently only possible on NVIDIA GPUs
        if gpuname.startswith('NVIDIA'):
            if gpuversions[i] == latest_nvidia_version:
                gpu_ver_string = ':white_check_mark: Up to date ({})'.format(gpuversions[i])
            else:
                gpu_ver_string = ':x: Not up to date ({})'.format(gpuversions[i])
                gpu_outdated = True
        else:
            gpu_ver_string = gpuversions[i]

        info.add_field(
            name='Driver Version',
            value=gpu_ver_string
        )

        # Add an empty 3rd field, since otherwise the ordering would look weird with more than one GPU installed
        info.add_field(
            name='\u200b',
            value='\u200b'
        )

        # If the GPU driver we're currently looking at is outdated and the
        # update notice is not yet in the quick fixes, add it
        if gpu_outdated and ' - Update GPU drivers' not in quickfixes.description:
            if '`/systemuptodate`' not in quickfixes.description:
                quickfixes.description += '`/systemuptodate`\n'
            quickfixes.description += ' - Update GPU drivers\n'

    fd.seek(0)
    return info, quickfixes
