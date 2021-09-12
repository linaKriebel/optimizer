import json

from minizinc import Instance, Model, Solver, Status
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

for it in items:
    # get item price (profit)
    profit.append(get_item_price(it))

# get all resources that are found in the current round of each job in the order
resources = get_results_of_jobs(order)
n = len(resources) # number of resources

names = []
for resource in resources:
    names.append(get_resource_name(resource, "full"))

jobtype = []
item = []

workflow = [{"set": [-1]} for i in range(m)]

ranking = [[] for i in range(n)] 
prices = [[] for i in range(n)] 
busy = [[] for i in range(n)] 

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
            price = get_price(row) # TODO job, reasource instead of row!

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

    "profit": profit,
    "target": target,

    "iso": iso,

    "jobtype": jobtype,
    "workflow": workflow,
    "item": item, 

    "ranking": ranking, 
    "price": prices,
    #"busy": busy
}

with open('d.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

#### START MINIZINC ####
status = Status.UNSATISFIABLE

asgn = Model("./asgn.mzn")
gecode = Solver.lookup("gecode")

c = 0
while status == Status.UNSATISFIABLE:
    print("no result found with given data")
    data["target"] = target - (c/100)

    with open('d.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    instance = Instance(gecode, asgn)    
    instance.add_file("./d.json")
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


