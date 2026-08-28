import hashlib
import json
from datetime import datetime, timezone
from db import now

DEFAULTS = {
    'positive_weight': 1.0, 'negative_weight': 1.0,
    'uncertainty_penalty': 0.35, 'primary_source_bonus': 0.15,
    'issuer_source_bonus': 0.08, 'relevance_floor': 0.20,
    'confidence_floor': 0.35, 'priced_in_penalty': 0.25,
    'impact_weight': 1.0,
}
BOUNDS = {
    'positive_weight': (0.25, 3.0), 'negative_weight': (0.25, 3.0),
    'uncertainty_penalty': (0.0, 1.5), 'primary_source_bonus': (0.0, 0.75),
    'issuer_source_bonus': (0.0, 0.75), 'relevance_floor': (0.0, 0.8),
    'confidence_floor': (0.0, 0.9), 'priced_in_penalty': (0.0, 1.0),
    'impact_weight': (0.25, 2.0),
}
POSITIVE = {'gain','growth','approval','surge','rise','record','profit','beat','adoption','partnership','launch','rally'}
NEGATIVE = {'loss','fall','ban','crisis','collapse','hack','fraud','sanction','war','recession','miss','outage','lawsuit'}
UNCERTAIN = {'may','might','could','rumor','reportedly','uncertain','alleged'}


class NewsLearning:
    def __init__(self, db):
        self.db = db
        self.ensure()

    def ensure(self):
        with self.db.con() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS news_model_versions(
              id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
              version INTEGER NOT NULL UNIQUE, status TEXT NOT NULL,
              parameters_json TEXT NOT NULL, parent_version INTEGER,
              source TEXT NOT NULL, reason TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS news_local_evaluations(
              news_id TEXT PRIMARY KEY, evaluated_at TEXT NOT NULL,
              model_version INTEGER NOT NULL, score TEXT NOT NULL,
              details_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS news_model_candidates(
              id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
              status TEXT NOT NULL, base_version INTEGER NOT NULL,
              sample_count INTEGER NOT NULL, sample_fingerprint TEXT NOT NULL,
              active_loss TEXT NOT NULL, candidate_loss TEXT NOT NULL,
              improvement TEXT NOT NULL, agreement_active TEXT NOT NULL,
              agreement_candidate TEXT NOT NULL, parameters_json TEXT NOT NULL,
              comparison_json TEXT NOT NULL, reason TEXT NOT NULL, decided_at TEXT);
            """)
            cols = {x['name'] for x in self.db.rows('PRAGMA table_info(news_model_candidates)')}
            additions = (
                ('training_count', 'INTEGER NOT NULL DEFAULT 0'),
                ('validation_count', 'INTEGER NOT NULL DEFAULT 0'),
                ('training_start_at', 'TEXT'), ('training_end_at', 'TEXT'),
                ('validation_start_at', 'TEXT'), ('validation_end_at', 'TEXT'),
                ('window_policy_json', "TEXT NOT NULL DEFAULT '{}'"),
                ('walk_forward_json', "TEXT NOT NULL DEFAULT '[]'"),
                ('stable_window_count', 'INTEGER NOT NULL DEFAULT 0'),
                ('required_stable_windows', 'INTEGER NOT NULL DEFAULT 0')
            )
            for name, definition in additions:
                if name not in cols:
                    c.execute(f'ALTER TABLE news_model_candidates ADD COLUMN {name} {definition}')
            c.execute('INSERT OR IGNORE INTO news_model_versions(created_at,version,status,parameters_json,parent_version,source,reason) VALUES(?,1,?,?,NULL,?,?)',
                      (now(), 'ACTIVE', json.dumps(DEFAULTS, sort_keys=True), 'DEFAULT', 'Deterministische lokale Ausgangsversion'))

    def active(self):
        return self.db.rows("SELECT * FROM news_model_versions WHERE status='ACTIVE' ORDER BY version DESC LIMIT 1")[0]

    @staticmethod
    def _number(value, default=0.0):
        try: return float(value)
        except (TypeError, ValueError): return default

    @staticmethod
    def _label(value, mapping):
        if isinstance(value, (int, float)): return max(-1.0, min(1.0, float(value)))
        return mapping.get(str(value or '').strip().lower(), 0.0)

    def _teacher(self, result):
        sentiment = self._label(result.get('sentiment'), {'positive':1,'bullish':1,'negative':-1,'bearish':-1,'neutral':0,'mixed':0})
        impact = abs(self._label(result.get('expected_impact'), {'high':1,'strong':1,'medium':.6,'moderate':.6,'low':.25,'none':0}))
        relevance = max(0.0, min(1.0, self._number(result.get('relevance'))))
        confidence = max(0.0, min(1.0, self._number(result.get('confidence'))))
        return sentiment * impact * relevance * confidence

    def _local(self, row, params):
        words = set(str((row.get('title') or '') + ' ' + (row.get('summary') or '')).lower().replace('-', ' ').split())
        raw = len(words & POSITIVE) * params['positive_weight'] - len(words & NEGATIVE) * params['negative_weight']
        raw -= len(words & UNCERTAIN) * params['uncertainty_penalty']
        if row.get('source_class') == 'primary': raw += params['primary_source_bonus']
        if row.get('source_class') == 'issuer': raw += params['issuer_source_bonus']
        result = row.get('teacher') or {}
        if self._number(result.get('relevance')) < params['relevance_floor']: raw = 0
        if self._number(result.get('confidence')) < params['confidence_floor']: raw = 0
        if result.get('priced_in') is True: raw *= 1 - params['priced_in_penalty']
        return max(-1.0, min(1.0, raw * params['impact_weight']))

    def data_status(self, required=10):
        """Return transparent, non-trading diagnostics for the comparison sample."""
        def count(sql):
            try:
                rows = self.db.rows(sql)
            except Exception:
                return 0
            return int(rows[0]['n']) if rows else 0
        news_items = count('SELECT COUNT(*) AS n FROM news_items')
        ai_total = count('SELECT COUNT(*) AS n FROM external_news_ai_results')
        ai_valid = count("SELECT COUNT(*) AS n FROM external_news_ai_results WHERE status='VALID'")
        ai_invalid = count("SELECT COUNT(*) AS n FROM external_news_ai_results WHERE status!='VALID'")
        sample_count = len(self._samples())
        missing = max(0, int(required) - sample_count)
        if news_items == 0:
            reason = 'NO_NEWS_ITEMS'
        elif ai_valid == 0:
            reason = 'NO_VALID_AI_RESULTS'
        elif missing:
            reason = 'INSUFFICIENT_VALID_AI_RESULTS'
        else:
            reason = 'READY'
        return {'status': reason, 'news_items': news_items, 'ai_total': ai_total,
                'ai_valid': ai_valid, 'ai_invalid': ai_invalid,
                'ai_unprocessed': max(0, news_items - ai_total),
                'sample_count': sample_count, 'required': int(required),
                'missing': missing, 'ready': missing == 0}

    def _samples(self):
        cols = {x['name'] for x in self.db.rows('PRAGMA table_info(news_items)')}
        time_expr = "COALESCE(n.published_at,n.fetched_at,a.created_at)" if {'published_at','fetched_at'}.issubset(cols) else 'a.created_at'
        try:
            rows = self.db.rows(f"SELECT n.id,n.title,n.summary,s.source_class,a.result_json,{time_expr} AS observed_at FROM news_items n JOIN news_sources s ON s.name=n.source_name JOIN external_news_ai_results a ON a.news_id=n.id WHERE a.status='VALID' ORDER BY observed_at,n.id")
        except Exception:
            return []
        out=[]
        for row in rows:
            try: teacher=json.loads(row.pop('result_json') or '{}')
            except Exception: continue
            row['teacher']=teacher;row['target']=self._teacher(teacher);out.append(row)
        return out

    @staticmethod
    def _timestamp(row):
        value=row.get('observed_at')
        if not value:return None
        try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)
        except (TypeError,ValueError):return None

    def _split(self, rows, validation_ratio=.30, minimum_validation=3):
        ratio=min(.50,max(.20,float(validation_ratio)))
        validation_count=max(int(minimum_validation),int(len(rows)*ratio))
        validation_count=min(validation_count,max(1,len(rows)-1))
        ordered=sorted(rows,key=lambda x:(self._timestamp(x) or datetime.min.replace(tzinfo=timezone.utc),str(x['id'])))
        training,validation=ordered[:-validation_count],ordered[-validation_count:]
        def edge(part,first):
            if not part:return None
            item=part[0] if first else part[-1]
            return item.get('observed_at')
        policy={'kind':'EXPANDING_TIME_SPLIT','validation_ratio':ratio,'minimum_validation':int(minimum_validation),
                'training_count':len(training),'validation_count':len(validation),
                'training_start_at':edge(training,True),'training_end_at':edge(training,False),
                'validation_start_at':edge(validation,True),'validation_end_at':edge(validation,False),
                'no_overlap':not set(x['id'] for x in training)&set(x['id'] for x in validation)}
        return training,validation,policy

    def _walk_forward(self, rows, params, active_params, windows=3, minimum_validation=3, minimum_improvement=.01):
        windows=max(2,min(8,int(windows)))
        minimum_validation=max(2,int(minimum_validation))
        ordered=sorted(rows,key=lambda x:(self._timestamp(x) or datetime.min.replace(tzinfo=timezone.utc),str(x['id'])))
        required=minimum_validation*(windows+1)
        if len(ordered)<required:
            return {'status':'INSUFFICIENT','required':required,'available':len(ordered),'windows':[]}
        first_training=len(ordered)-minimum_validation*windows
        results=[]
        for index in range(windows):
            validation_start=first_training+index*minimum_validation
            training=ordered[:validation_start]
            validation=ordered[validation_start:validation_start+minimum_validation]
            active=self._evaluate(validation,active_params);candidate=self._evaluate(validation,params)
            improvement=active['loss']-candidate['loss']
            passed=improvement>=minimum_improvement and candidate['agreement']>=active['agreement']
            results.append({'index':index+1,'training_count':len(training),'validation_count':len(validation),
              'training_end_at':training[-1].get('observed_at'),'validation_start_at':validation[0].get('observed_at'),
              'validation_end_at':validation[-1].get('observed_at'),'active':active,'candidate':candidate,
              'improvement':improvement,'passed':passed})
        stable=sum(x['passed'] for x in results)
        return {'status':'VALID','window_count':windows,'stable_window_count':stable,'windows':results}

    def _evaluate(self, rows, params):
        if not rows:return {'loss':1.0,'agreement':0.0,'samples':0}
        predictions=[self._local(x,params) for x in rows]
        targets=[x['target'] for x in rows]
        loss=sum(abs(a-b) for a,b in zip(predictions,targets))/len(rows)
        agreement=sum((a>0)==(b>0) if a and b else abs(a-b)<.25 for a,b in zip(predictions,targets))/len(rows)
        return {'loss':loss,'agreement':agreement,'samples':len(rows)}

    def _optimize(self, rows, active):
        candidate=dict(active);steps={'positive_weight':.1,'negative_weight':.1,'uncertainty_penalty':.05,'primary_source_bonus':.05,'issuer_source_bonus':.05,'relevance_floor':.05,'confidence_floor':.05,'priced_in_penalty':.05,'impact_weight':.1}
        best=self._evaluate(rows,candidate)['loss'];evaluated=1
        for _ in range(8):
            improved=False
            for name,step in steps.items():
                for direction in (-1,1):
                    trial=dict(candidate);lo,hi=BOUNDS[name];trial[name]=round(max(lo,min(hi,trial[name]+step*direction)),4);loss=self._evaluate(rows,trial)['loss'];evaluated+=1
                    if loss<best-1e-12:candidate,best,improved=trial,loss,True
            if not improved:break
        self._last_search_details={'algorithm':'coordinate_search_v52','evaluated':evaluated,'training_count':len(rows),'best_loss':best}
        return candidate

    def propose(self, min_sample=10, min_improvement=.01, automatic=False, validation_ratio=.30, minimum_validation=3, walk_forward_windows=3, required_stable_windows=2):
        rows=self._samples();n=len(rows)
        if n < min_sample:
            diagnostic = self.data_status(min_sample)
            return {'status': 'INSUFFICIENT_DATA', 'sample_count': n,
                    'required': min_sample, 'missing': diagnostic['missing'],
                    'reason': diagnostic['status'], 'data_status': diagnostic}
        training,validation,policy=self._split(rows,validation_ratio,minimum_validation)
        if len(training)<2 or len(validation)<minimum_validation:
            return {'status':'INSUFFICIENT_VALIDATION','sample_count':n,'training_count':len(training),'validation_count':len(validation)}
        fingerprint=hashlib.sha256('|'.join(x['id'] for x in rows).encode()).hexdigest()
        previous=self.db.rows('SELECT id,status FROM news_model_candidates WHERE sample_fingerprint=? ORDER BY id DESC LIMIT 1',(fingerprint,))
        if automatic and previous:return {'status':'UNCHANGED','candidate_id':previous[0]['id'],'candidate_status':previous[0]['status'],'sample_count':n}
        active=self.active();active_params=json.loads(active['parameters_json']);candidate=self._optimize(training,active_params)
        train_old=self._evaluate(training,active_params);train_new=self._evaluate(training,candidate)
        old=self._evaluate(validation,active_params);new=self._evaluate(validation,candidate);improvement=old['loss']-new['loss']
        walk=self._walk_forward(rows,candidate,active_params,walk_forward_windows,minimum_validation,min_improvement)
        required_stable=max(1,min(int(required_stable_windows),int(walk_forward_windows)))
        stable_ok=walk['status']=='VALID' and walk['stable_window_count']>=required_stable
        passed=policy['no_overlap'] and improvement>=min_improvement and new['agreement']>=old['agreement'] and candidate!=active_params and stable_ok
        status='PENDING' if passed else 'REJECTED_GATE'
        comparison={'training':{'active':train_old,'candidate':train_new},'validation':{'active':old,'candidate':new},
                    'minimum_validation_improvement':min_improvement,'automatic_comparison':bool(automatic),'window_policy':policy,'walk_forward':walk,'required_stable_windows':required_stable}
        reason='Zeitlich getrennte Validierung bestanden; ausdrÃƒÂ¼ckliche Freigabe erforderlich' if passed else 'Validierungs- oder Vergleichsgate nicht erfÃƒÂ¼llt'
        values=(now(),status,active['version'],n,fingerprint,str(old['loss']),str(new['loss']),str(improvement),str(old['agreement']),str(new['agreement']),json.dumps(candidate,sort_keys=True),json.dumps(comparison,sort_keys=True),reason,None if passed else now(),len(training),len(validation),policy['training_start_at'],policy['training_end_at'],policy['validation_start_at'],policy['validation_end_at'],json.dumps(policy,sort_keys=True),json.dumps(walk,sort_keys=True),walk.get('stable_window_count',0),required_stable)
        with self.db.con() as c:
            cur=c.execute('INSERT INTO news_model_candidates(created_at,status,base_version,sample_count,sample_fingerprint,active_loss,candidate_loss,improvement,agreement_active,agreement_candidate,parameters_json,comparison_json,reason,decided_at,training_count,validation_count,training_start_at,training_end_at,validation_start_at,validation_end_at,window_policy_json,walk_forward_json,stable_window_count,required_stable_windows) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',values);candidate_id=cur.lastrowid
        self.db.audit('NEWS_MODEL_CANDIDATE',json.dumps({'candidate_id':candidate_id,'status':status,'samples':n,'validation_improvement':improvement,'window_policy':policy,'walk_forward':walk,'required_stable_windows':required_stable},sort_keys=True))
        return {'status':status,'candidate_id':candidate_id,'sample_count':n,'training_count':len(training),'validation_count':len(validation),'improvement':improvement,'agreement_active':old['agreement'],'agreement_candidate':new['agreement'],'window_policy':policy,'walk_forward':walk,'required_stable_windows':required_stable}

    def decide(self, candidate_id, action):
        found=self.db.rows('SELECT * FROM news_model_candidates WHERE id=?',(candidate_id,))
        if not found:return {'status':'NOT_FOUND'}
        item=found[0]
        if item['status']!='PENDING':return {'status':'NOT_PENDING'}
        active=self.active()
        if int(active['version'])!=int(item['base_version']):
            with self.db.con() as c:c.execute("UPDATE news_model_candidates SET status='STALE',decided_at=? WHERE id=?",(now(),candidate_id))
            return {'status':'STALE'}
        if action=='reject':
            with self.db.con() as c:c.execute("UPDATE news_model_candidates SET status='REJECTED',decided_at=? WHERE id=?",(now(),candidate_id))
            return {'status':'REJECTED'}
        if action!='approve':return {'status':'INVALID_ACTION'}
        params=json.loads(item['parameters_json'])
        if set(params)!=set(DEFAULTS):return {'status':'INVALID_PARAMETER_SET'}
        for key,value in params.items():
            lo,hi=BOUNDS[key]
            if not lo<=float(value)<=hi:return {'status':'OUT_OF_BOUNDS','parameter':key}
        rows=self._samples();policy=json.loads(item.get('window_policy_json') or '{}')
        training,validation,current_policy=self._split(rows,policy.get('validation_ratio',.30),policy.get('minimum_validation',3))
        fingerprint=hashlib.sha256('|'.join(x['id'] for x in rows).encode()).hexdigest()
        old=self._evaluate(validation,json.loads(active['parameters_json']));check=self._evaluate(validation,params)
        comparison=json.loads(item['comparison_json'])
        required=float(comparison.get('minimum_validation_improvement',.01))
        stored_walk=comparison.get('walk_forward') or {}
        required_stable=int(item.get('required_stable_windows') or comparison.get('required_stable_windows') or 1)
        walk=self._walk_forward(rows,params,json.loads(active['parameters_json']),stored_walk.get('window_count',3),policy.get('minimum_validation',3),required)
        stable_ok=walk['status']=='VALID' and walk['stable_window_count']>=required_stable
        valid=(fingerprint==item['sample_fingerprint'] and current_policy['no_overlap'] and old['loss']-check['loss']>=required and check['agreement']>=old['agreement'] and stable_ok)
        if not valid:
            with self.db.con() as c:c.execute("UPDATE news_model_candidates SET status='REJECTED_RECHECK',decided_at=? WHERE id=?",(now(),candidate_id))
            self.db.audit('NEWS_MODEL_APPROVAL_BLOCKED',json.dumps({'candidate_id':candidate_id,'sample_unchanged':fingerprint==item['sample_fingerprint']}),'warning')
            return {'status':'REJECTED_RECHECK'}
        version=int(active['version'])+1
        with self.db.con() as c:
            c.execute("UPDATE news_model_versions SET status='SUPERSEDED' WHERE status='ACTIVE'")
            c.execute('INSERT INTO news_model_versions(created_at,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,?,?,?,?,?)',(now(),version,'ACTIVE',item['parameters_json'],active['version'],f'APPROVED_CANDIDATE_{candidate_id}','Explizite Benutzerfreigabe nach zeitlich getrennter Validierung'))
            c.execute("UPDATE news_model_candidates SET status='APPROVED',decided_at=? WHERE id=?",(now(),candidate_id))
        self.db.audit('NEWS_MODEL_APPROVED',json.dumps({'candidate_id':candidate_id,'version':version,'validation_count':len(validation)}))
        return {'status':'APPROVED','version':version}

    def refresh_local(self):
        active=self.active();params=json.loads(active['parameters_json'])
        rows=self.db.rows("SELECT n.id,n.title,n.summary,s.source_class FROM news_items n JOIN news_sources s ON s.name=n.source_name")
        with self.db.con() as c:
            for row in rows:
                score=self._local(row,params)
                c.execute('INSERT INTO news_local_evaluations(news_id,evaluated_at,model_version,score,details_json) VALUES(?,?,?,?,?) ON CONFLICT(news_id) DO UPDATE SET evaluated_at=excluded.evaluated_at,model_version=excluded.model_version,score=excluded.score,details_json=excluded.details_json',(row['id'],now(),active['version'],str(score),json.dumps({'parameters':params},sort_keys=True)))
        return {'status':'VALID','evaluated':len(rows),'version':active['version']}

    def candidates(self):return self.db.rows('SELECT * FROM news_model_candidates ORDER BY id DESC LIMIT 100')
    def versions(self):return self.db.rows('SELECT * FROM news_model_versions ORDER BY version DESC')
