import logging
import enum

from dataclasses import dataclass, field
from typing import List
from minizinc import Instance, Model, Solver, Status, error

from collector import AssignmentData

ISO_CONSTRAINT = """
                constraint forall(j1 in JOB) (
                    forall(j2 in workflow[j1]) (
                        (jobtype[j1] = TRA /\ jobtype[j2] = REV) -> assigned[j1] != assigned[j2]
                    )
                ); 
                """
PROJECT_MARGIN_CONSTRAINT = "constraint profit_margin >= target;"

class AssignmentStatus(enum.Enum):
    UNSATISFIABLE = 1
    OPTIMAL = 2
    ALTERNATIVE = 3
    ERROR = 4

@dataclass
class AssignmentResult:
    k: int # number of items

    status: AssignmentStatus = AssignmentStatus.OPTIMAL
    message: str = "A valid assignment of resources to all job that optimizes the given objectives was found." 

    assignment: List = field(default_factory=list)

    items: List = field(default_factory=list)
    
    project_margin: float = 0.0
    capacity_violations: int = 0
    parallel_violations: int = 0

    def __post_init__(self):
        self.optimal_costs = [0 for i in range(self.k)]
        self.optimal_quality = [0 for i in range(self.k)]

@dataclass
class ItemResult:
    midx: int   
    constrained: bool
    target_margin: float
    
    margin_weight: int
    quality_weight: int

    constraint: str = ""
    optimal_costs: float = 0.0
    optimal_margin: float = 0.0
    actual_margin: float = 0.0
    optimal_quality: float = 0.0
    actual_quality: float = 0.0

    satisfiable: bool = True
    distance: float = 0.0

    def __post_init__(self):
        if self.constrained:
            self.constraint = f"constraint margin[{self.midx}] >= item_targets[{self.midx}];"

    def update_constraint(self, target):
        self.constraint = f"constraint margin[{self.midx}] >= {target};"

def add_data(instance, data: AssignmentData):
    instance["n"] = data.n
    instance["m"] = data.m
    instance["k"] = data.k
    instance["l"] = data.l
    instance["profit"] = data.profit
    instance["item_targets"] = data.item_targets
    instance["target"] = data.target
    instance["target_weights"] = data.target_weights
    instance["ranking_weights"] = data.ranking_weights
    instance["jobtype"] = data.jobtype
    instance["workflow"] = data.workflow
    instance["item"] = data.item
    instance["ranking"] = data.ranking
    instance["price"] = data.price
    instance["schedule"] = data.schedule
    instance["planned"] = data.planned

def opt(instance: Instance, objective):
    with instance.branch() as child:

        child.add_string(objective)

        try:
            result = child.solve()
        except error as err:
            logging.error(f"An error occurred while trying to find optimal value for '{objective}': {err.message}")
            return None

        if result.status != Status.OPTIMAL_SOLUTION:
            logging.error(f"No solution found for '{objective}': {result.status}")
            return None

        return result
     
def solve(data: AssignmentData, iso, target_active, steps):

    model = Model("assign.mzn")
    cbc = Solver.lookup("cbc") # MIP solver   
    instance = Instance(cbc, model)

    add_data(instance, data)

    result = AssignmentResult(data.k)
    items = [ItemResult(i+1, data.item_constraints[i], data.item_targets[i], data.target_weights[i], data.ranking_weights[i]) for i in range(data.k)]

    # 1) check if the problem instance has any data inconsistencies
    with instance.branch() as child:
        child.add_string("obj = 0.0;")
        try:
            child.solve()
        except error.MiniZincAssertionError as err:
            # there must be an error in the problem instance, e.g. not every job has at least one matching resource
            logging.info(err) 
            result.status = AssignmentStatus.ERROR
            result.message = "A valid assignment is not possible. Please check whether each job has at least one matching resource."
            return result

    # 2) check optional ISO constraint 
    if iso:
        # add ISO 17100 constraint to model instance
        logging.info("ISO constraint added")
        instance.add_string(ISO_CONSTRAINT)

        with instance.branch() as child:
            child.add_string("obj = 0.0;")
            res = child.solve()
            if res.status == Status.UNSATISFIABLE:
                # the ISO constraint prevents a valid solution to be found
                logging.info("UNSATISFIABLE: ISO constraint")
                result.status = AssignmentStatus.UNSATISFIABLE
                result.message = """A valid assignment that is ISO 17100 compliant is not possible. \n 
                                    In order to solve this problem you could change or remove selection criteria from 
                                    the jobs in order to find more or different matching resources."""
                return result

    # 3) check for each item
    objective = "constraint obj = "
    for i, item in enumerate(items):

        # search for optimal values of individual objectives
        # --> costs / margin
        res = opt(instance, f"obj = obj_costs[{item.midx}];")
        
        if not res:
            # something went wrong
            result.status = AssignmentStatus.ERROR
            result.message = "Something went wrong!"
            return result
        
        item.optimal_costs = res.objective
        item.optimal_margin = res["margin"][i]
        
        # check if the item's target profit margin would be met, if the constraint is active
        if item.constrained and item.optimal_margin < item.target_margin:
            # no, the problem instance will be UNSATISFIABLE
            logging.info(f"UNSATISFIABLE: item {data.items[i]} target profit margin constraint.")
            result.status = AssignmentStatus.ALTERNATIVE
            result.message = "At least one of the items' target profit margins cannot be reached. You could consider to lower them."
        
            item.satisfiable = False
            # update the constraint to at least reach the optimal target profit margin
            item.update_constraint(item.optimal_margin)
            item.distance = item.target_margin-item.optimal_margin 

        # --> quality     
        res = opt(instance, f"obj = obj_quality[{item.midx}];")

        if not res:
            # something went wrong
            result.status = AssignmentStatus.ERROR
            result.message = "Something went wrong!"
            return result

        item.optimal_quality = res.objective
        
        # put together weighted item objective
        objective += f"({item.margin_weight}*(obj_costs[{item.midx}]/{item.optimal_costs}) + {item.quality_weight}*(obj_quality[{item.midx}]/{item.optimal_quality})) + " 

    # add soft constraint costs
    objective += f"parallel_violations + capacity_violations;"

    # add objective
    instance.add_string(objective)
    logging.debug(objective)

    # try to find a solution without the target profit margin constraints
    logging.info("Start search without target profit margin constraints")
    res = instance.solve()
    logging.info(f"Solution found after {res.statistics['time']}")
    solution = res.solution
    
    # add the (adjusted) items' target profit margin constraints if active
    for item in items:
        if item.constrained:
            logging.info(f"Item target profit margin constraint added for item {item.midx}")
            instance.add_string(item.constraint)
            
    # check if the problem instance is still solvable
    logging.info("Start search with item target profit margin constraints")
    res = instance.solve()
    logging.info(f"Solution found after {res.statistics['time']}")
    if res.status == Status.OPTIMAL_SOLUTION:
        # yes, override the solution
        solution = res.solution

        # add the project margin constraint if active
        if target_active:
            logging.info("Project target profit margin constraint added")
            instance.add_string(PROJECT_MARGIN_CONSTRAINT)

            #check if the problem instance is still solvable
            logging.info("Start search with all active constraints")
            res = instance.solve()
            logging.info(f"Solution found after {res.statistics['time']}")
            if res.status == Status.OPTIMAL_SOLUTION:
                # yes, override the solution
                solution = res.solution
            else:
                logging.info("UNSATISFIABLE: project target profit margin constraint")
                result.status = AssignmentStatus.ALTERNATIVE
                result.message = "The project's target profit margin cannot be reached. You could consider to lower it."                        

    # update the item information
    for i, item in enumerate(items):
        item.actual_margin = solution.margin[i]
        item.actual_quality = solution.obj_quality[i]

    result.assignment = solution.assigned
    
    result.items = items

    result.project_margin = solution.profit_margin
    result.capacity_violations = solution.capacity_violations
    result.parallel_violations = solution.parallel_violations
    
    logging.debug(solution)
        
    return(result)