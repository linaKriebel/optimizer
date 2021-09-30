import sys

from connector import *
from db_connector import *
from mini import *
from soap_connector import *

if __name__ == "__main__":

    ORDER = 1
    
    # parse arguments
    if len(sys.argv)>1:
        ORDER = sys.argv[1]

    # get data from database
    data = get_data(ORDER)

    iso = is_iso_active(ORDER)
    target = is_target_profit_margin_active()

    resources = get_results_of_jobs(ORDER)
    jobs = get_jobs(ORDER)

    # call minizinc
    result = solve(data, iso, target, 10)
    print(result)

    # parse minizinc result
    assignment = {}
    if result:
        for i in range(len(jobs)):
            round_id = get_current_round(jobs[i])
            resource_id = resources[result["assigned"][i]-1]

            assignment[round_id] = resource_id

    print(assignment)

    # send results to bm
    # uuid = login()
    # for round_id, resource_id in assignment.items():
    #     data = set_resource(uuid, resource_id, round_id)
    #     #print(data)
