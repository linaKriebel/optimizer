enum JOBTYPE = {TRA, REV, DTP};

int: n; % number of resources
int: m; % number of jobs
int: k; % number of items

int: l; % number of days in project

set of int: RESOURCE = 1..n;
set of int: JOB = 1..m;
set of int: ITEM = 1..k;
set of int: DAY = 1..l;

array[ITEM] of float: profit; % profit of each item
array[ITEM] of float: item_targets; % target margin for each item
float: target; % target margin for the project

array[ITEM] of int: target_weights;
array[ITEM] of int: ranking_weights;

array[JOB] of JOBTYPE: jobtype; 
array[JOB] of set of -1..m: workflow;
array[JOB] of ITEM: item; 

array[RESOURCE,JOB] of int: ranking;
array[RESOURCE,JOB] of int: price;

array[RESOURCE,DAY] of int: schedule;
array[JOB,DAY] of int: planned;

% check data plausibility
constraint forall(j in JOB)(
  assert(exists(r in RESOURCE)(ranking[r,j] > 0), "There is no matching resource for job \(j)")
);

% assignment variable
array[JOB] of var RESOURCE: assigned;

% objective values
array[ITEM] of var float: obj_costs;
array[ITEM] of var float: obj_quality;

% other variables
array[ITEM] of var int: costs;
array[ITEM] of var float: margin;
var float: profit_margin;

var int: parallel_violations;
var int: capacity_violations;

var float: obj;

% profit margin = (profit - cost) / profit
constraint forall(i in ITEM)(sum(j in JOB where item[j] = i) (price[assigned[j],j]) = costs[i]);
constraint forall(i in ITEM)(((profit[i] - costs[i]) / profit[i]) = margin[i]);
constraint profit_margin = ((sum(i in ITEM)(profit[i]) - sum(i in ITEM)(costs[i])) / sum(i in ITEM)(profit[i]));

% quality objective function
constraint forall(i in ITEM)(sum(j in JOB where item[j] = i)(ranking[assigned[j], j])/sum(j in JOB where item[j] = i)(1) = obj_quality[i]);

% costs objective function
constraint forall(i in ITEM)(sum(j in JOB where item[j] = i) (price[assigned[j],j])/sum(j in JOB where item[j] = i)(1) = obj_costs[i]);

% HARD CONSTRAINTS

% the assigned resource must have the required skills for the job
constraint forall(j in JOB)(ranking[assigned[j], j] > 0);

% SOFT CONSTRAINTS

% jobs that are running in parallel should not be done by the same resource
constraint parallel_violations = sum(j1, j2 in JOB where j1 < j2)(
  let {
    	array[DAY] of var bool:p1 = [planned[j1,d]>0| d in DAY];
    	array[DAY] of var bool:p2 = [planned[j2,d]>0| d in DAY];
  } in (p1 = p2) /\ (assigned[j1] = assigned[j2]));

% a resource should not take more jobs than their capacity allows
constraint capacity_violations = sum(r in RESOURCE, d in DAY)(
  let {
    var int: capacity = (schedule[r,d] - sum(j in JOB where assigned[j] = r)(planned[j,d]))
  } in capacity < 0
);

solve minimize obj;

output["assigned = \(assigned);\nmargin = \(margin);\ncosts = \(costs);\nquality = \(obj_quality);\nprofit margin = \(profit_margin);\ncapacity violations = \(capacity_violations);\nparallel violations = \(parallel_violations);\nobj = \(obj)"];