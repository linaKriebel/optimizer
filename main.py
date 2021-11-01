import sys
import logging

import collector
import dbconnector
import minimizer 
import bmconnector

if __name__ == "__main__":

    ORDER = 173
    HOSTNAME = "qa30.plunet.com"

    logging.basicConfig(filename='logger.log', format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d/%m/%y %H:%M:%S', level=logging.INFO)

    # parse arguments [scriptname, order, host]
    if len(sys.argv) > 1:
        ORDER = sys.argv[1]
        HOSTNAME = sys.argv[2]

    # get data from database
    logging.info("Start collecting data from database")
    data = collector.get_data(ORDER)
    logging.info("Finished collecting data from database")

    iso_active = dbconnector.is_iso_active(ORDER)
    target_active = dbconnector.is_target_profit_margin_active()

    # call minizinc
    logging.info("Start optimization process")
    result = minimizer.solve(data, iso_active, target_active, 10)

    # connect to bm
    bmconnector.login(HOSTNAME)

    statistics = ""

    if result.status == minimizer.AssignmentStatus.ERROR or result.status == minimizer.AssignmentStatus.UNSATISFIABLE:
        statistics = result.message
        bmconnector.set_description(ORDER, statistics)

    if result.status == minimizer.AssignmentStatus.ALTERNATIVE:
        statistics += f"No valid solution for the given constraints could be found. A valid alternative is suggested.\n"

        if target_active and result.target < data.target: 
            statistics += f"original target profit margin had to be lowered by {round((data.target-result.project_margin)*100,2)}% to {round(result.project_margin*100,2)}% \n"
        else:
            statistics += f"project profit margin: {round(result.project_margin*100,2)}%"            
        statistics += f"{result.parallel_violations} parallel assignments \n{result.capacity_violations} capacities exceeded"

        bmconnector.set_description(ORDER, statistics) 
        print(statistics)

        for i, item_id in enumerate(data.items):
            item_result = result.items[i]
            note = bmconnector.get_note(item_id)

            item_statistics = note + "\n---------------\n"

            if item_result.satisfiable:
                item_statistics += f"target profit margin of {round(item_result.target_margin*100,2)}% was reached or exceeded: {round(item_result.actual_margin*100,2)}% \n"
            else:
                item_statistics += f"original target profit margin of {round(item_result.target_margin*100,2)}% was lowered by {round(item_result.distance*100,2)}% to {round(item_result.actual_margin*100,2)}% \n"
                
            delta = round((item_result.actual_margin/item_result.optimal_margin)*100)
            item_statistics += f"profit margin {round(item_result.actual_margin*100,2)}% "
            if delta >= 100.0:
                item_statistics += "##########"
            else:
                for i in range(0,100,10):
                    if i in range(delta):
                        item_statistics += "#"
                    else:
                        item_statistics += "="
            item_statistics += f" {round(item_result.optimal_margin*100,2)}%\n"

            delta = round((item_result.optimal_quality/item_result.actual_quality)*100)
            item_statistics += f"quality {round(item_result.actual_quality,2)} "
            if delta >= 100.0:
                item_statistics += "##########"
            else:
                for i in range(0,100,10):
                    if i in range(delta):
                        item_statistics += "#"
                    else:
                        item_statistics += "="
            item_statistics += f" {round(item_result.optimal_quality,2)}\n"
            
            bmconnector.set_note(item_id, item_statistics)
            print(item_statistics)
    
    if result.status == minimizer.AssignmentStatus.OPTIMAL:
        statistics += f"""{result.message}
                project profit margin: {round(result.project_margin*100,2)}%
                {result.parallel_violations} parallel assignments
                {result.capacity_violations} capacities exceeded"""

        bmconnector.set_description(ORDER, statistics) 
        print(statistics)

        for i, item_id in enumerate(data.items):
            item_result = result.items[i]
            note = bmconnector.get_note(item_id)

            item_statistics = note + "\n---------------\n"

            item_statistics += f"target profit margin of {round(item_result.target_margin*100,2)}% was reached or exceeded: {round(item_result.actual_margin*100,2)}% \n"
            delta = round((item_result.actual_margin/item_result.optimal_margin)*100)
            item_statistics += f"profit margin {round(item_result.actual_margin*100,2)}% "
            if delta >= 100.0:
                item_statistics += "##########"
            else:
                for i in range(0,100,10):
                    if i in range(delta):
                        item_statistics += "#"
                    else:
                        item_statistics += "="
            item_statistics += f" {round(item_result.optimal_margin*100,2)}%\n"

            delta = round((item_result.optimal_quality/item_result.actual_quality)*100)
            item_statistics += f"quality {round(item_result.actual_quality,2)} "
            if delta >= 100.0:
                item_statistics += "##########"
            else:
                for i in range(0,100,10):
                    if i in range(delta):
                        item_statistics += "#"
                    else:
                        item_statistics += "="
            item_statistics += f" {round(item_result.optimal_quality,2)}\n"
            
            bmconnector.set_note(item_id, item_statistics)
            print(item_statistics)
        
        for i, job in enumerate(data.jobs):
            round_id = dbconnector.get_current_round(job)
            resource_id = data.resources[result.assignment[i]-1] # minizinc index 1..n vs. 0..n-1
            # send results to bm
            bmconnector.set_resource(resource_id, round_id)
        
