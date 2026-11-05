"""Season preparation and the existing three exact-action human confirmations."""
import json
from .. import lineage,season_lineage
from ..history import canonical_json as encode,digest

PROFILE='bridge-season-control-3'
POLICY='supported-ecosystem-proposal-1'


class SeasonControls:
    def __init__(self,controls):self.controls=controls;self.career=controls.career

    def prepare(self,request_id,policy):
        if policy!=POLICY:raise ValueError('Explicit supported season policy required')
        with self.controls.access() as c:
            old=c.execute('SELECT manifest FROM preparations WHERE id=?',(request_id,)).fetchone()
            if old:manifest=json.loads(old[0])
            else:
                with lineage.access(self.career.registry,self.career.key) as (lc,t):
                    info,_=season_lineage.current(lc,t,self.career.key)
                first=info.get('profile')!=season_lineage.PROFILE
                op={'kind':'lifecycle_setup' if first else 'lifecycle_following',
                    'args':{'scenario':'full-2028-proposal-1' if first else 'repeat-season-proposal-1'}}
                manifest=season_lineage.prepare(self.career.registry,self.career.key,request_id,[op],
                                               transition=True,automatic_gameplay=True)
                c.execute('INSERT INTO preparations VALUES(?,?)',(request_id,encode(manifest)));self.controls._seal(c)
        if manifest.get('profile')!=season_lineage.PROFILE:raise ValueError('Preparation belongs to another profile')
        return self.summary(manifest)

    def manifest(self,identifier):
        value=self.controls.manifest(identifier)
        if value.get('profile')!=season_lineage.PROFILE:raise ValueError('Registered season preparation required')
        return value

    def summary(self,manifest):
        return {'control_profile':PROFILE,'preparation_id':manifest['request_id'],'manifest_sha256':digest(manifest),
                'policy_sha256':digest(manifest['policy']),'career_seed_sha256':manifest['career_seed_sha256'],
                'review':{'season':manifest['season'],'automatic_gameplay_after_acceptance':manifest['automatic_gameplay'],
                          'model_versions':manifest['policy'],
                          'initial_execution_scope':'2028 setup includes chronological ACCESS bootstrap football through January 10; later seasons prepare the calendar without playing it.' if manifest['season']==2028 else 'Offseason and calendar preparation; ordinary episodes execute subsequent fixtures.',
                          'explicit_proposals':['modeled economics/ages/youth','missing state/federation and foreign entry evidence'],
                          'historical_results_invented':False,'separate_successor_acceptance_required':True}}

    def statement(self,action,identifier):
        who,receipt=self.controls.trusted();m=self.manifest(identifier)
        with lineage.access(self.career.registry,self.career.key) as (c,t):
            row=c.execute('SELECT * FROM batches WHERE id=?',('season3:'+identifier,)).fetchone()
        candidate=None
        if who['checkpoint']!=m['immediate_parent_sha256']:raise ValueError('Stale season preparation')
        if action=='authorize_batch':
            if row:raise ValueError('Season already authorized; resume its original action')
        elif action=='execute_batch':
            if not row or row['state']!='season_authorized_v3':raise ValueError('Separate policy approval required')
        elif action=='accept_candidate':
            if not row or row['state']!='season_candidate':raise ValueError('Verified season candidate required')
            candidate={'checkpoint_sha256':row['checkpoint'],'package_sha256':row['package_sha'],'independently_verified':True}
        else:raise ValueError('Unknown season control stage')
        return {'profile':PROFILE,'action':action,'preparation_id':identifier,'career':self.career.career,
                'test_only':self.career.test_only,'repository_id':self.controls.gate.context['repository_id'],
                'parent_sha256':m['immediate_parent_sha256'],'manifest_sha256':digest(m),'policy_receipt_sha256':receipt,
                'target_sha256':candidate['checkpoint_sha256'] if candidate else digest(m),
                'candidate':candidate,'review':self.summary(m)['review']}

    def request(self,action,identifier,request_id,issue):
        statement=self.statement(action,identifier)
        return {'review':statement['review'],'candidate':statement['candidate'],
                'confirmation':self.controls.gate.challenge(request_id,issue,statement)}

    def perform(self,statement):
        # Controls.perform has already authenticated the durable exact human proof.
        who,receipt=self.controls.trusted();m=self.manifest(statement['preparation_id'])
        if (statement['career']!=who['career'] or statement['test_only'] is not who['test_only']
            or statement['repository_id']!=self.controls.gate.context['repository_id']
            or statement['parent_sha256']!=m['immediate_parent_sha256'] or statement['manifest_sha256']!=digest(m)
            or statement['policy_receipt_sha256']!=receipt or statement['review']!=self.summary(m)['review']):
            raise ValueError('Season confirmation binding changed')
        action=statement['action'];reg,key=self.career.registry,self.career.key
        if action in {'authorize_batch','execute_batch'} and statement['target_sha256']!=digest(m):
            raise ValueError('Exact season manifest confirmation required')
        if action=='authorize_batch':
            season_lineage.authorize(reg,key,m,lineage.signed(season_lineage.authorization(m),key))
            return {'execution_authorized':True,'executed':False,'test_only':who['test_only']}
        destination=self.controls._destination(m['request_id'])
        if action=='execute_batch':return season_lineage.execute(reg,key,m['request_id'],destination)
        if action!='accept_candidate':raise ValueError('Unknown season stage')
        decision=season_lineage.acceptance_template(reg,key,destination)
        if decision['checkpoint_sha256']!=statement['target_sha256']:raise ValueError('Exact season candidate confirmation required')
        return season_lineage.accept(reg,key,destination,decision,lineage.sign(key,decision))
