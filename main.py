import sys

from data_collector import *
from db_connector import *
from mini import *
from soap_connector import *

if __name__ == "__main__":

    ORDER = 173
    HOSTNAME = "qa30.plunet.com"

    # parse arguments [scriptname, order, host]
    if len(sys.argv) > 1:
        ORDER = sys.argv[1]
        HOSTNAME = sys.argv[2]

    # get data from database
    print("### fetch data from database")
    data = get_data(ORDER)

    iso = is_iso_active(ORDER)
    target = is_target_profit_margin_active()

    resources = get_results_of_jobs(ORDER)
    jobs = get_jobs(ORDER)

    # call minizinc
    print("### start optimization")
    result = solve(data, iso, target, 10)
    print(result)

    uuid = login(HOSTNAME)

    if result:
        # parse minizinc result
        for i in range(len(jobs)):
            round_id = get_current_round(jobs[i])
            resource_id = resources[result["assigned"][i]-1]

            # send results to bm
            status = set_resource(uuid, resource_id, round_id)
            print(status)

    # TODO give some useful statistics to the user   
