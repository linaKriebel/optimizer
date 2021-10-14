import json
    
from dataclasses import dataclass, field
from datetime import timedelta, date
from typing import List

from db_connector import *

@dataclass
class AssignmentData:
    n: int
    m: int
    k: int
    l: int

    profit: List = field(default_factory=list)
    item_targets: List = field(default_factory=list)
    target: float = 0.0

    target_weights: List = field(default_factory=list)
    ranking_weights: List = field(default_factory=list)

    jobtype: List = field(default_factory=list)
    workflow: List = field(default_factory=list)
    item: List = field(default_factory=list)

    ranking: List = field(default_factory=list)
    price: List = field(default_factory=list)

    schedule: List = field(default_factory=list)
    planned: List = field(default_factory=list)

    def __post_init__(self):
        self.workflow = [{"set": [-1]} for i in range(self.m)]
        self.ranking = [[] for i in range(self.n)] 
        self.price = [[] for i in range(self.n)] 
        self.schedule = [[] for i in range(self.n)]
        self.planned = [[0 for x in range(self.l)] for i in range(self.m)]

    def get_number_of_jobs(self, idx):
        no = 0
        for i in self.item:
            if i == idx: no += 1           
        return no

@dataclass
class Job:
    id: int
    index: int

    item_index: int = 0
    jobtype: str = ''
    current_round_id: int = 0
    start_date: date = 0
    end_date: date = None
    planned_time: int = None

def get_item_target(note, order):
    split = note.split("-")

    if len(split) == 3:
        item_target = float(split[0])
    else:
        # use project target profit margin as default for item
        item_target = get_project_target(order)

    return item_target

def get_target_weight(note):
    split = note.split("-")

    if len(split) == 3:
        target_weight = int(split[1])
    else:
        target_weight = 1

    return target_weight

def get_ranking_weight(note):
    split = note.split("-")

    if len(split) == 3:
        ranking_weight = int(split[2])
    else:
        ranking_weight = 1

    return ranking_weight

#deprecated (not formatted like that anymore)
def parse_price(price):
    if price:
        price = price.replace("*", "") # remove possible minimum price indicator
        price = price.replace(" EUR", "") # remove currency
        price = price.replace(".", "") # remove unnecessary de separator
        price = price.replace(",", ".") # switch to en decimal separator
        price = float(price) # convert to float value
        price = round(price) # convert to int value
        return price
    else:
        return 0

def get_data(order):

    items = get_items(order)
    jobs = get_jobs(order)
    resources = get_results_of_jobs(order)

    order_start = get_order_startdate(order)
    order_end = get_order_enddate(order)
    days = (order_end - order_start).days # number of days between start and end date
    
    # create data object with dimensions
    data = AssignmentData(len(resources),len(jobs),len(items),days)

    data.target = get_project_target(order)

    for it in items:
        # get item price (profit)
        data.profit.append(get_item_price(it))

        # get item note, that constains item target profit margin and weightings
        note = get_item_note(it)

        # parse note (<target>-<weight>-<weight>)
        if note:
            data.item_targets.append(get_item_target(note, order))
            data.target_weights.append(get_target_weight(note))
            data.ranking_weights.append(get_ranking_weight(note))

    for r, resource in enumerate(resources):

        # weekday (0-6) of order (start) date
        weekday = order_start.weekday()
        
        for i in range(days):
            # calculate weekday
            weekday = weekday % 7

            # get working hours / minutes of that resource for this weekday
            # TODO does not consider the correct weekly schedule yet
            working_hours = get_working_hours(resource, weekday)
            minutes = round(working_hours * 60)

            data.schedule[r].append(minutes)
            weekday += 1

    for i, job in enumerate(jobs):

        # get jobtype
        data.jobtype.append(get_jobtype(job))

        # get item
        data.item.append(get_item_of_job(job))
        
        # get workflow
        successors = get_successors(job)
        if successors:
            # format sets for MiniZinc as dict --> "set": []
            data.workflow[i]["set"] = [jobs.index(succ)+1 for succ in successors] # minizinc index starts with 1

        # get planned time
        pt = get_planned_time(job) / 1000 # in seconds

        # get start and end date
        start = get_job_startdate(job)
        end = get_job_enddate(job)

        delta = (end - start).days

        # rate = planned time per day
        rate = round((pt / delta) * 0.0003, 2) # in hours
        rate = round(rate * 60) # in minutes

        day = start

        for d in range(delta):
            idx = (day - order_start).days
            data.planned[i][idx] = rate

            day += timedelta(days=1)

        for j, resource in enumerate(resources):

            # check if resource is in results list
            if is_result(job, resource):
                data.ranking[j].append(get_rank(job, resource))
                # TODO get price by job and resource instead of row
                price = round(get_price(get_result_row(job, resource))) # rounded to int value
                data.price[j].append(price)
            else:
                # resource is not in results list, set default values
                data.ranking[j].append(0)
                data.price[j].append(0)

    # # create data file (optional)
    # with open('data.json', 'w', encoding='utf-8') as f:
    #     json.dump(data.__dict__, f, ensure_ascii=False, indent=4)

    return data