enum JOBTYPE = {TRA, REV, DTP};

int: n; % number of resources
int: m; % number of jobs
int: k; % number of items

set of int: RESOURCE = 1..n;
set of int: JOB = 1..m;
set of int: ITEM = 1..k;

array[ITEM] of float: profit; % profit of the item
float: target; % target margin for the item

bool: iso;

array[JOB] of JOBTYPE: jobtype; 
array[JOB] of set of -1..m: workflow;
array[JOB] of ITEM: item; 

array[RESOURCE,JOB] of int: ranking;
array[RESOURCE,JOB] of float: price;

array[JOB] of var RESOURCE: assigned;

array[ITEM] of var int: costs;
array[ITEM] of var 0.0..1.0: margin;
var 0.0..1.0: profit_margin;

var int: parallel_violations;

var int: obj;

constraint obj = 1 * sum(i in ITEM)(costs[i]) + 9 * sum(j in JOB)(ranking[assigned[j], j] * 10) + (parallel_violations * 10);

%constraint obj = sum(i in ITEM)(costs[i])
%  + 9 * costs[1] + 1 * sum(j in JOB where item[j] = 1)(ranking[assigned[j], j])
%  + 1 * costs[2] + 9 * sum(j in JOB where item[j] = 2)(ranking[assigned[j], j]);

% margin = profit - cost / profit
constraint forall(i in ITEM)(sum(j in JOB where item[j] = i) (price[assigned[j],j]) = costs[i]);
constraint forall(i in ITEM)(((profit[i] - costs[i]) / profit[i]) = margin[i]);

% the assigned resource must have the required skills for the job
constraint forall(j in JOB)(ranking[assigned[j], j] > 0);

% ISO 17100: a TRA followed by a REV cannot be done by the same resource
constraint if(iso) then (
  forall(j1 in JOB) (
    forall(j2 in workflow[j1]) (
        (jobtype[j1] = TRA /\ jobtype[j2] = REV) -> assigned[j1] != assigned[j2]
    )
  )
) endif;

% SOFT
% jobs that are running in parallel should not be done by the same resource
constraint parallel_violations = sum(j1, j2 in JOB where j1 < j2 /\ workflow[j1] = workflow[j2])(assigned[j1] != assigned[j2]);

% SOFT
% a resource cannot take more jobs than their capacity allows
% constraint forall(r in RESOURCE)(sum(j in JOB where assigned[j] = r)(vol[r,j]) <= capacity[r]);

% HARD
% target margin for the project must be met
constraint profit_margin = ((sum(i in ITEM)(profit[i]) - sum(i in ITEM)(costs[i])) / sum(i in ITEM)(profit[i]));
constraint profit_margin >= target;

% HARD
% target margin for each item must be met as well
constraint forall(i in ITEM)(margin[i] >= target);

solve minimize obj;

output["jobtype = \(jobtype);\nassigned = \(assigned);\nmargin = \(margin);\nprofit margin = \(profit_margin);\ncosts = \(costs);"]