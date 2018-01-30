import datetime
from enum import Enum


class Channel(Enum):
    ESR = "ESR"
    RELEASE = "RELEASE"
    CANDIDATE = "CANDIDATE"
    BETA = "BETA"
    AURORA = "AURORA"
    NIGHTLY = "NIGHTLY"


class Status(Enum):
    ERROR = "error"
    INCOMPLETE = "incomplete"
    MISSING = "missing"
    EXISTS = "exists"


def version_parts(parts):
    patch = '0'
    major = parts[0]
    minor = parts[1]
    if len(parts) > 2:
        patch = parts[2]
    return major, minor, patch


def strip_candidate_info(version):
    if 'rc' in version:  # 57.0b8rc3
        return version.split('rc')[0]
    elif 'build' in version:  # 57.0build4
        return version.split('build')[0]
    return version


def build_version_id(version):
    channel = '0'

    version = strip_candidate_info(version)

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


def get_version_channel(product, version):  # pragma: no cover
    if version.endswith('esr'):
        return Channel.ESR
    elif 'build' in version or 'rc' in version:
        return Channel.CANDIDATE
    elif 'a' in version:
        return Channel.NIGHTLY
    elif 'b' in version:
        if product == 'devedition':
            return Channel.AURORA
        return Channel.BETA
    else:
        return Channel.RELEASE


def get_version_from_filename(filename):
    parts = filename.split('-', 1)[1].split('.')[:-2]  # Remove firefox- and .tar.bz2
    return '.'.join([p for p in parts if p[0].isdigit()])


def is_valid_version(version):
    try:
        build_version_id(version)
        return True
    except IndexError:
        return False


def yesterday(*, formating='%Y-%m-%d', days=1):
    return(datetime.date.today() - datetime.timedelta(days=days)).strftime(formating)
