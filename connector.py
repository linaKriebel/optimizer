import json

from minizinc import Instance, Model, Solver, Status
from datetime import date, timedelta
from db_connector import *

#### FETCH DATA ####
order = '1'

# get target profit margin (Zielrendite)
target = get_project_target(order)

# is iso active?
iso = is_iso_active(order)

# get all items from order
items = get_items(order)
k = len(items) # number of items

# get all jobs from order
jobs = get_jobs(order)
m = len(jobs) # number of jobs

profit = []
targets = []

target_weights = []
ranking_weights = []

for it in items:
    # get item price (profit)
    profit.append(get_item_price(it))

    # get item note
    note = get_item_note(it)

    # parse note (target-weight_for_target-weight_for_rank)
    if note:
        item_target,weight_target,weight_rank = note[0][0].split("-")
    else:
        item_target,weight_target,weight_rank = 0


# get all resources that are found in the current round of each job in the order
resources = get_results_of_jobs(order)
n = len(resources) # number of resources

# get order start and end date
order_start = get_order_startdate(order)
order_end = get_order_enddate(order)
days = (order_end - order_start).days # number of days between start and end date

names = []
schedule = [[] for i in range(n)]

r = 0
for resource in resources:
    names.append(get_resource_name(resource, "full")) # get full name

    # weekday (0-6) of order (start) date
    day = order_start.weekday()
    
    for i in range(days):
        # calculate weekday
        day = day % 7

        # get working hours / minutes of that resource for this weekday
        # TODO does not consider the "right" weekly schedule yet
        working_hours = get_working_hours(resource, day) # returns the working hours
        minutes = round(working_hours * 60)

        schedule[r].append(minutes)
        day += 1

    r += 1

jobtype = []
item = []

workflow = [{"set": [-1]} for i in range(m)]

ranking = [[] for i in range(n)] 
prices = [[] for i in range(n)] 
busy = [[] for i in range(n)] 

planned = [[0 for x in range(days)] for i in range(m)]

i = 0
for job in jobs:

    # get jobtype
    jobtype.append(get_jobtype(job))

    # get item
    item.append(get_item_of_job(job))
    
    # get workflow
    successors = get_successors(job)
    if successors:
        workflow[i]["set"] = [jobs.index(succ)+1 for succ in successors] # minizinc index starts with 1

    # get planned time
    pt = get_planned_time(job) / 1000 # in seconds

    # get start end end date
    start = get_job_startdate(job)
    end = get_job_enddate(job)

    delta = (end - start).days
    rate = round((pt / delta) * 0.0003, 2) # in hours
    rate = round(rate * 60) # in minutes

    day = start

    for d in range(delta):
        idx = (day - order_start).days
        planned[i][idx] = rate

        day += timedelta(days=1)

    j = 0
    for resource in resources:

        if is_result(job, resource):
            row = get_result_row(job, resource)
            ranking[j].append(get_rank(job, resource))
            busy[j].append(get_busy(job, resource))
        else:
            row = None
            ranking[j].append(0)
            busy[j].append(0)

        if row:
            # get price
            price = get_price(row) # TODO job, resource instead of row!

            if price:
                price = price.replace("*", "") # remove possible minimum price indicator
                price = price.replace(" EUR", "") # remove currency
                price = price.replace(".", "") # remove unnecessary de separator
                price = price.replace(",", ".") # switch to en decimal separator
                price = float(price) # convert to float value
                price = round(price) # convert to int value

                prices[j].append(price)
        else:
            prices[j].append(0)

        j += 1
    i += 1

#### FORMAT DATA FOR MINIZINC####

data = {
    "n": n,
    "m": m,
    "k": k,
    "l": days,

    "profit": profit,
    "item_targets": targets,
    "target": target,

    "iso": iso,

    "target_weights": target_weights,
    "ranking_weights": ranking_weights,

    "jobtype": jobtype,
    "workflow": workflow,
    "item": item, 

    "ranking": ranking, 
    "price": prices,
    "schedule": schedule, 
    "planned": planned
}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

#### START MINIZINC ####
status = Status.UNSATISFIABLE

asgn = Model("./assign.mzn")
gecode = Solver.lookup("gecode")

c = 0
while status == Status.UNSATISFIABLE:
    print("no result found with given data")
    data["target"] = target - (c/100)

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    instance = Instance(gecode, asgn)    
    instance.add_file("./data.json")
    result = instance.solve()
    status = result.status
    
    c += 1

#### OUTPUT ####
if result:
    d = dict.fromkeys(jobs)
    for i in range(m):
        d[jobs[i]] = names[result["assigned"][i]-1]
    print(d)

print(result)


