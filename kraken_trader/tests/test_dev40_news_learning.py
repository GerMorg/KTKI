import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from db import DB, now
from news_learning import NewsLearning


def seeded(tmp_path):
    db=DB(str(tmp_path/'news.db'));db.init();nl=NewsLearning(db)
    with db.con() as c:
        c.execute("CREATE TABLE news_sources(name TEXT PRIMARY KEY,source_class TEXT)")
        c.execute("CREATE TABLE news_items(id TEXT PRIMARY KEY,title TEXT,summary TEXT,source_name TEXT)")
        c.execute("CREATE TABLE external_news_ai_results(news_id TEXT PRIMARY KEY,created_at TEXT,status TEXT,result_json TEXT,error TEXT)")
        c.execute("INSERT INTO news_sources VALUES('primary','primary')")
        for i in range(12):
            positive=i%2==0; title=('gain ' if positive else 'loss ')+str(i)
            ai={'relevance':1,'sentiment':'positive' if positive else 'negative','expected_impact':'medium','horizon':'short','confidence':1,'fact_status':'confirmed','priced_in':False,'topics':[],'affected_assets':[],'summary':'x','counterarguments':[]}
            c.execute("INSERT INTO news_items VALUES(?,?,?,'primary')",(str(i),title,''))
            c.execute("INSERT INTO external_news_ai_results VALUES(?,?,?,?,NULL)",(str(i),now(),'VALID',json.dumps(ai)))
    return db,nl


def test_news_candidate_requires_manual_approval(tmp_path):
    db,nl=seeded(tmp_path)
    result=nl.propose(min_sample=10,min_improvement=0)
    assert result['status']=='PENDING'
    assert nl.active()['version']==1
    approved=nl.decide(result['candidate_id'],'approve')
    assert approved['status']=='APPROVED'
    assert nl.active()['version']==2


def test_automatic_comparison_deduplicates_same_sample(tmp_path):
    db,nl=seeded(tmp_path)
    first=nl.propose(min_sample=10,min_improvement=0,automatic=True)
    second=nl.propose(min_sample=10,min_improvement=0,automatic=True)
    assert second['status']=='UNCHANGED'
    assert second['candidate_id']==first['candidate_id']


def test_active_local_model_is_persisted(tmp_path):
    db,nl=seeded(tmp_path)
    out=nl.refresh_local()
    assert out['evaluated']==12
    assert len(db.rows('SELECT * FROM news_local_evaluations'))==12



