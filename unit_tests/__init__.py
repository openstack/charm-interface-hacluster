# Patch out lsb_release() and get_platform() as unit tests should be fully
# insulated from the underlying platform.  Unit tests assume that the system is
# ubuntu jammy.
from unittest.mock import patch
patch(
    'charmhelpers.osplatform.get_platform', return_value='ubuntu'
).start()
patch(
    'charmhelpers.core.host.lsb_release',
    return_value={
        'DISTRIB_CODENAME': 'jammy'
    }).start()
