"""Registered season execution schema; legacy DEV migration remains frozen."""
from .schema import DDL as LEGACY_DDL

PROFILE = 'season-forward-lineage-3'
VERSION = 3
DDL = '''
CREATE TABLE ms_meta(id INTEGER PRIMARY KEY CHECK(id=1),profile TEXT NOT NULL,
 parent_checkpoint TEXT NOT NULL,parent_sha256 TEXT NOT NULL,policy_json TEXT NOT NULL,
 seed TEXT NOT NULL,clock TEXT NOT NULL,test_only INTEGER NOT NULL CHECK(test_only IN (0,1)));
''' + LEGACY_DDL[LEGACY_DDL.index('CREATE TABLE ms_migrations'):]


def policy(test_only):
    from .store import proposed_policy
    from .offseason import POLICY as OFFSEASON
    from .calendar import POLICY as CALENDAR
    from .domestic import POLICY as DOMESTIC
    from .continental_entry import POLICY as CONTINENTAL
    if type(test_only) is not bool:
        raise ValueError('Explicit authority mode required')
    return {**proposed_policy(), 'version': 'registered-season-execution-1',
            'test_only': test_only, 'approved_proposals_required': True,
            'offseason':OFFSEASON,'calendar':CALENDAR,'domestic':DOMESTIC,
            'continental':CONTINENTAL,'repeat_qualification':'prior-cup-and-explicit-foreign-order-proposal-1'}


def configuration(value):
    if not isinstance(value, dict) or value != policy(value.get('test_only')):
        raise ValueError('Unsupported registered season policy')
    return PROFILE, DDL, VERSION, value['test_only'], True
