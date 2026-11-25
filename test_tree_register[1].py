import tempfile, unittest, importlib.util
from pathlib import Path
from datetime import date
spec=importlib.util.spec_from_file_location("tree_register", Path(__file__).parents[1]/"tree_register.py")
tr=importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)

class RegisterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=(tr.BASE,tr.DATA,tr.EXPORTS,tr.CHARTS,tr.JSON_PATH,tr.CSV_PATH)
        tr.BASE=Path(self.tmp.name); tr.DATA=tr.BASE/"data"; tr.EXPORTS=tr.BASE/"exports"; tr.CHARTS=tr.BASE/"charts"
        tr.JSON_PATH=tr.DATA/"trees.json"; tr.CSV_PATH=tr.DATA/"trees.csv"
        self.r=tr.Register()
    def tearDown(self):
        tr.BASE,tr.DATA,tr.EXPORTS,tr.CHARTS,tr.JSON_PATH,tr.CSV_PATH=self.old
        self.tmp.cleanup()
    def test_add_and_id(self):
        x=self.r.add("Neem",10,"School",date.today().isoformat(),"NSS")
        self.assertEqual(x["tree_id"],"TR-0001")
    def test_follow_up_and_rate(self):
        x=self.r.add("Neem",10,"School",date.today().isoformat(),"NSS")
        self.r.follow_up(x["tree_id"],date.today().isoformat(),10,9)
        self.assertAlmostEqual(self.r.summary()["survival"],90)
    def test_reject_invalid_alive_count(self):
        x=self.r.add("Neem",10,"School",date.today().isoformat(),"NSS")
        with self.assertRaises(ValueError): self.r.follow_up(x["tree_id"],date.today().isoformat(),5,6)
    def test_search(self):
        self.r.add("Neem",10,"School Campus",date.today().isoformat(),"NSS")
        self.assertEqual(len(self.r.search(location="school")),1)
    def test_sample_only_when_empty(self):
        self.assertEqual(tr.seed_sample(self.r,3),3)
        self.assertEqual(tr.seed_sample(self.r,3),0)
    def test_summary_empty(self):
        self.assertEqual(self.r.summary()["records"],0)
        self.assertEqual(self.r.summary()["survival"],0)
    def test_duplicate_csv_import(self):
        f=Path(self.tmp.name)/"in.csv"
        f.write_text("tree_name,quantity,location,plantation_date,planted_by,notes\nNeem,4,Park,2026-01-01,Team,x\nNeem,4,Park,2026-01-01,Team,x\n")
        a,s,e=self.r.import_csv(f)
        self.assertEqual((a,s,len(e)),(1,1,0))
if __name__=="__main__": unittest.main()
