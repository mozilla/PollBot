import pkg_resources

# Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version

HTTP_API_VERSION = '1.2'
PRODUCTS = ('firefox', 'devedition')
