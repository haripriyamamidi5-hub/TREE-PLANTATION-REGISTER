"""Tree Plantation Register - Python mini project.
Stores plantation records in JSON and CSV, tracks survival follow-ups,
supports search, summaries, charts, report exports and duplicate-safe CSV import.
"""
from __future__ import annotations
import csv, json, re
from pathlib import Path
from datetime import date, datetime, timedelta
from statistics import mean

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
EXPORTS = BASE / "exports"
CHARTS = BASE / "charts"
JSON_PATH = DATA / "trees.json"
CSV_PATH = DATA / "trees.csv"
CSV_FIELDS = ["tree_id","tree_name","quantity","location","plantation_date","planted_by","notes","checks"]

def prepare():
    for folder in (DATA, EXPORTS, CHARTS):
        folder.mkdir(parents=True, exist_ok=True)

def text_value(value, label, limit=100, allow_blank=False):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    if not value and not allow_blank:
        raise ValueError(f"{label} cannot be blank")
    if len(value) > limit:
        raise ValueError(f"{label} must be at most {limit} characters")
    return value

def date_value(value, label="Date"):
    try:
        result = datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{label} must be YYYY-MM-DD")
    if result > date.today():
        raise ValueError(f"{label} cannot be in the future")
    return result.isoformat()

def integer(value, label, minimum=1, maximum=100000):
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a whole number")
    if not minimum <= result <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return result

class Register:
    def __init__(self):
        prepare()
        self.records = []
        self.load()

    def load(self):
        if not JSON_PATH.exists():
            self.save()
            return
        try:
            raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("Invalid register structure")
            self.records = [x for x in raw if isinstance(x, dict) and x.get("tree_id")]
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            backup = DATA / "trees_invalid_backup.json"
            if not backup.exists():
                shutil_copy = JSON_PATH.read_bytes()
                backup.write_bytes(shutil_copy)
            self.records = []
            print(f"WARNING: Data file was invalid and copied to {backup.name}: {exc}")

    def save(self):
        prepare()
        temp = JSON_PATH.with_suffix(".tmp")
        temp.write_text(json.dumps(self.records, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(JSON_PATH)
        self.write_csv()

    def write_csv(self):
        with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for rec in self.records:
                row = dict(rec)
                row["checks"] = json.dumps(rec.get("checks", []), ensure_ascii=False)
                writer.writerow(row)

    def next_id(self):
        nums = []
        for rec in self.records:
            match = re.fullmatch(r"TR-(\d+)", str(rec.get("tree_id", "")))
            if match:
                nums.append(int(match.group(1)))
        return f"TR-{max(nums, default=0)+1:04d}"

    @staticmethod
    def duplicate_key(row):
        return tuple(str(row.get(k, "")).strip().casefold() for k in
                     ("tree_name","quantity","location","plantation_date","planted_by"))

    def add(self, tree_name, quantity, location, plantation_date, planted_by, notes=""):
        rec = {
            "tree_id": self.next_id(),
            "tree_name": text_value(tree_name, "Tree name", 60),
            "quantity": integer(quantity, "Quantity"),
            "location": text_value(location, "Location", 120),
            "plantation_date": date_value(plantation_date, "Plantation date"),
            "planted_by": text_value(planted_by, "Planted by", 80),
            "notes": text_value(notes, "Notes", 500, True),
            "checks": []
        }
        self.records.append(rec)
        self.save()
        return rec

    def get(self, tree_id):
        return next((r for r in self.records if r["tree_id"].casefold() == tree_id.strip().casefold()), None)

    def follow_up(self, tree_id, check_date, inspected, alive, notes=""):
        rec = self.get(tree_id)
        if not rec:
            raise ValueError("Tree record ID not found")
        inspected = integer(inspected, "Inspected trees", 1, int(rec["quantity"]))
        alive = integer(alive, "Alive trees", 0, inspected)
        check = {"check_date": date_value(check_date, "Check date"),
                 "inspected": inspected, "alive": alive,
                 "notes": text_value(notes, "Notes", 300, True)}
        rec.setdefault("checks", []).append(check)
        rec["checks"].sort(key=lambda x: x["check_date"])
        self.save()
        return check

    def search(self, keyword="", location=""):
        keyword, location = keyword.casefold().strip(), location.casefold().strip()
        return [r for r in self.records
                if (not keyword or keyword in " ".join([r["tree_id"],r["tree_name"],r["planted_by"],r.get("notes","")]).casefold())
                and (not location or location in r["location"].casefold())]

    def summary(self):
        checks = [c for r in self.records for c in r.get("checks", [])]
        inspected = sum(int(c["inspected"]) for c in checks)
        alive = sum(int(c["alive"]) for c in checks)
        rates = [100*int(c["alive"])/int(c["inspected"]) for c in checks if int(c["inspected"])]
        return {"records":len(self.records),
                "trees":sum(int(r["quantity"]) for r in self.records),
                "locations":len({r["location"].casefold() for r in self.records}),
                "inspected":inspected, "alive":alive,
                "survival":100*alive/inspected if inspected else 0.0,
                "average":mean(rates) if rates else 0.0}

    def import_csv(self, filename):
        added, skipped, errors = 0, 0, []
        required = {"tree_name","quantity","location","plantation_date","planted_by"}
        try:
            with Path(filename).open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                if not required.issubset(set(reader.fieldnames or [])):
                    raise ValueError("CSV is missing required columns")
                existing = {self.duplicate_key(r) for r in self.records}
                for line, row in enumerate(reader, 2):
                    try:
                        key = self.duplicate_key(row)
                        if key in existing:
                            skipped += 1
                            continue
                        self.add(row["tree_name"], row["quantity"], row["location"],
                                 row["plantation_date"], row["planted_by"], row.get("notes",""))
                        existing.add(key)
                        added += 1
                    except Exception as exc:
                        errors.append(f"Row {line}: {exc}")
        except Exception as exc:
            errors.append(str(exc))
        (EXPORTS / "import_errors.txt").write_text(
            "\n".join(errors) if errors else "No import errors.\n", encoding="utf-8")
        return added, skipped, errors

    def overdue(self, interval_days=90):
        today = date.today()
        result = []
        for rec in self.records:
            last = max((c["check_date"] for c in rec.get("checks", [])), default=rec["plantation_date"])
            due = datetime.strptime(last, "%Y-%m-%d").date() + timedelta(days=interval_days)
            if due < today:
                result.append((rec["tree_id"], rec["tree_name"], rec["location"], due.isoformat()))
        return result

def seed_sample(register, count=40):
    if register.records:
        return 0
    names = ["Neem","Mango","Banyan","Peepal","Guava","Jamun","Teak","Amla"]
    places = ["School Campus","Community Park","Main Road","Lake View","College Garden"]
    planters = ["NSS Unit","Green Team","Eco Club","Volunteers"]
    for i in range(count):
        planted = (date.today() - timedelta(days=150 + (i*11)%300)).isoformat()
        rec = register.add(names[i%len(names)], 5+(i*7)%30, places[i%len(places)],
                           planted, planters[i%len(planters)], "Demonstration record")
        inspected = min(rec["quantity"], max(2, rec["quantity"]-1))
        alive = max(0, inspected-(i%3))
        checked = (date.today()-timedelta(days=(i*3)%60)).isoformat()
        register.follow_up(rec["tree_id"], checked, inspected, alive, "Demonstration follow-up")
    return count

def create_charts(register):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        raise RuntimeError("Install dependencies with: python -m pip install -r requirements.txt")
    monthly = {}
    for rec in register.records:
        month = rec["plantation_date"][:7]
        monthly[month] = monthly.get(month, 0) + int(rec["quantity"])
    fig, ax = plt.subplots(figsize=(8,4))
    months = sorted(monthly)
    ax.plot(months, [monthly[m] for m in months], marker="o")
    ax.set_title("Trees Planted by Month"); ax.set_xlabel("Month"); ax.set_ylabel("Trees")
    ax.tick_params(axis="x", rotation=45); ax.grid(True, alpha=.3); fig.tight_layout()
    first = CHARTS/"plantation_trend.png"; fig.savefig(first, dpi=140); plt.close(fig)
    alive = sum(int(c["alive"]) for r in register.records for c in r.get("checks", []))
    inspected = sum(int(c["inspected"]) for r in register.records for c in r.get("checks", []))
    fig, ax = plt.subplots(figsize=(6,4))
    if inspected:
        ax.pie([alive, inspected-alive], labels=["Alive","Not alive"], autopct="%1.1f%%", startangle=90)
    else:
        ax.text(.5,.5,"No follow-up data",ha="center",va="center")
    ax.set_title("Survival Check Distribution"); fig.tight_layout()
    second = CHARTS/"survival_distribution.png"; fig.savefig(second, dpi=140); plt.close(fig)
    return [first, second]

def export_reports(register):
    s = register.summary()
    report = ["TREE PLANTATION REGISTER - EXECUTIVE SUMMARY", "",
              f"Plantation records: {s['records']}", f"Total trees planted: {s['trees']}",
              f"Unique locations: {s['locations']}", f"Trees inspected: {s['inspected']}",
              f"Alive in recorded checks: {s['alive']}", f"Overall survival rate: {s['survival']:.2f}%",
              f"Average check survival: {s['average']:.2f}%", "", "FOLLOW-UP WARNINGS"]
    warnings = register.overdue()
    report.extend([f"{a} | {b} | {c} | overdue since {d}" for a,b,c,d in warnings] or ["No overdue follow-ups."])
    summary_file = EXPORTS/"executive_summary.txt"
    summary_file.write_text("\n".join(report)+"\n", encoding="utf-8")
    audit_file = EXPORTS/"audit_log.txt"
    audit_file.write_text("\n".join(
        f"{r['tree_id']} | {r['tree_name']} | {r['quantity']} | {r['location']} | {r['plantation_date']} | checks={len(r.get('checks',[]))}"
        for r in register.records)+"\n", encoding="utf-8")
    register.write_csv()
    return [summary_file, audit_file, CSV_PATH]

def show(records):
    if not records:
        print("No records found."); return
    print(f'{"ID":<9} {"TREE":<12} {"QTY":>4}  {"LOCATION":<22} {"PLANTED":<10} {"CHECKS":>6}')
    print("-"*75)
    for r in records:
        print(f'{r["tree_id"]:<9} {r["tree_name"]:<12} {r["quantity"]:>4}  {r["location"][:22]:<22} {r["plantation_date"]:<10} {len(r.get("checks",[])):>6}')

def menu():
    register = Register()
    print("\nTREE PLANTATION REGISTER\nRecord | Monitor | Protect | Grow Green")
    while True:
        print("\n1 Add plantation record\n2 Record survival follow-up\n3 View all records\n4 Search / filter records\n5 Executive summary\n6 Generate charts\n7 Export reports\n8 Import CSV\n9 Overdue follow-up warnings\n10 Load 40 sample records (empty register only)\n0 Save and exit")
        choice = input("Choose an option: ").strip()
        try:
            if choice == "1":
                r = register.add(input("Tree name: "), input("Quantity: "), input("Location: "),
                                 input("Plantation date (YYYY-MM-DD): "), input("Planted by: "), input("Notes: "))
                print("Saved successfully. Tree record ID:", r["tree_id"])
            elif choice == "2":
                tid = input("Tree record ID: ")
                inspected = input("Inspected trees: ")
                alive = input("Alive trees: ")
                c = register.follow_up(tid, input("Check date (YYYY-MM-DD): "), inspected, alive, input("Notes: "))
                print("Survival check saved:", c)
            elif choice == "3": show(register.records)
            elif choice == "4": show(register.search(input("Keyword: "), input("Location contains: ")))
            elif choice == "5":
                s=register.summary()
                print("\nEXECUTIVE SUMMARY")
                print(f"Plantation records       : {s['records']}\nTotal trees planted      : {s['trees']}\nUnique locations         : {s['locations']}\nTrees inspected          : {s['inspected']}\nAlive in recorded checks : {s['alive']}\nOverall survival rate    : {s['survival']:.2f}%\nAverage check survival   : {s['average']:.2f}%")
            elif choice == "6":
                for p in create_charts(register): print("Chart created:", p.relative_to(BASE))
            elif choice == "7":
                for p in export_reports(register): print("Exported:", p.relative_to(BASE))
            elif choice == "8":
                n, skipped, errors = register.import_csv(input("CSV file path: ").strip().strip('"'))
                print(f"Imported {n} records; skipped {skipped} duplicates; {len(errors)} errors.")
            elif choice == "9":
                warnings=register.overdue()
                print("\n".join(" | ".join(x) for x in warnings) if warnings else "No overdue follow-ups.")
            elif choice == "10":
                n=seed_sample(register)
                print(f"Loaded {n} sample records." if n else "Sample data loads only into an empty register.")
            elif choice == "0":
                register.save(); print("Data saved. Goodbye."); break
            else: print("Choose a valid option from 0 to 10.")
        except (ValueError, OSError, RuntimeError) as exc:
            print("ERROR:", exc)

if __name__ == "__main__":
    try: menu()
    except (EOFError, KeyboardInterrupt): print("\nProgram closed safely.")
