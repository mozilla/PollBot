from enum import Enum


class Channel(Enum):
    ESR = "ESR"
    RELEASE = "RELEASE"
    BETA = "BETA"
    NIGHTLY = "NIGHTLY"


def version_parts(parts):
    patch = '0'
    major = parts[0]
    minor = parts[1]
    if len(parts) > 2:
        patch = parts[2]
    return major, minor, patch


def build_version_id(version):
    channel = '0'
    if 'a' in version:
        parts, channel = version.split('a')
        parts = parts.split('.')
        release_code = 'a'
    elif 'b' in version:
        parts, channel = version.split('b')
        parts = parts.split('.')
        release_code = 'b'
    elif version.endswith('esr'):
        parts = version.strip('esr').split('.')
        release_code = 'x'
    else:
        parts = version.split('.')
        release_code = 'r'

    major, minor, patch = version_parts(parts)
    return '{}{}{}{}{}'.format(major.zfill(3), minor.zfill(3), patch.zfill(3),
                               release_code, channel.zfill(3))


def get_version_channel(version):  # pragma: no cover
    if version.endswith('esr'):
        return Channel.ESR
    elif 'a' in version:
        return Channel.NIGHTLY
    elif 'b' in version:
        return Channel.BETA
    else:
        return Channel.RELEASE


def get_version_from_filename(filename):
    parts = filename.split('.', 2)
    return '{}.{}'.format(parts[0].split('-')[1], parts[1])
