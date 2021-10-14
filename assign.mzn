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

array[JOB] of var RESOURCE: assigned;

array[ITEM] of var int: costs;
array[ITEM] of var float: margin;
var float: profit_margin;

array[ITEM] of var float: quality;

array[RESOURCE,DAY] of var int: capacity;

var int: parallel_violations;
var int: capacity_violations;

var float: obj;

% profit margin = (profit - cost) / profit
constraint forall(i in ITEM)(sum(j in JOB where item[j] = i) (price[assigned[j],j]) = costs[i]);
constraint forall(i in ITEM)(((profit[i] - costs[i]) / profit[i]) = margin[i]);
constraint profit_margin = ((sum(i in ITEM)(profit[i]) - sum(i in ITEM)(costs[i])) / sum(i in ITEM)(profit[i]));

% quality = sum(rank of assigned resource) per job of item
constraint forall(i in ITEM)(sum(j in JOB where item[j] = i)(ranking[assigned[j], j])/sum(j in JOB where item[j] = i)(1) = quality[i]);

% HARD CONSTRAINTS

% the assigned resource must have the required skills for the job
constraint forall(j in JOB)(ranking[assigned[j], j] > 0);

% SOFT CONSTRAINTS

% jobs that are running in parallel should not be done by the same resource
constraint parallel_violations = sum(j1, j2 in JOB where j1 < j2 /\ workflow[j1] = workflow[j2])(assigned[j1] != assigned[j2]);

% a resource should not take more jobs than their capacity allows
constraint forall(r in RESOURCE, d in DAY)((schedule[r,d] - sum(j in JOB where assigned[j] = r)(planned[j,d])) = capacity[r,d]);
constraint capacity_violations = sum(r in RESOURCE, d in DAY)(capacity[r,d] < 0);

% (optional) REV should be less expensive than TRA
% constraint forall(j1 in JOB) (
%    forall(j2 in workflow[j1]) (
%        (jobtype[j1] = TRA /\ jobtype[j2] = REV) -> price[assigned[j1],j1] >= price[assigned[j2],j2]
%    )
%  );

solve minimize obj;

output["assigned = \(assigned);\nmargin = \(margin);\ncosts = \(costs);\nquality = \(quality);\nprofit margin = \(profit_margin);\ncapacity violations = \(capacity_violations);\nparallel violations = \(parallel_violations);\nobj = \(obj)"];