from rest_framework.response import Response
from rest_framework.decorators import api_view
from pulp import LpMinimize, LpMaximize, LpProblem, LpStatus, LpStatusNotSolved, lpSum, LpVariable


def getStatus(value):
    if value == LpStatus.OPTIMAL:
        return "Solved"
    elif value == LpStatus.INFEASIBLE:
        return "Infeasible"
    elif value == LpStatus.UNBOUNDED:
        return "Unbounded"
    elif value == LpStatusNotSolved:
        return "Not solved"



@api_view(['GET'])
def getData(request):

    model = LpProblem(name="small-problem", sense=LpMaximize)

    x = LpVariable(name="soya", lowBound=0)
    y = LpVariable(name="beans", lowBound=0)

    model += (2 * x + y <= 20, 'red_constraint')
    model += (4 * x - 5 * y >= -10, 'blue_constraint')
    model += (-x + 2 * y >= -2, 'yellow_constraint')
    model += (-x + 5 * y == 15, 'green_constraint')

    objective = lpSum([x, 2 * y])
    model += objective

    status = model.solve()

    print(f"status: {model.status}, {LpStatus[model.status]}")
    print(f"objective: {model.objective.value()}")

    variables = []

    for var in model.variables():
        variables.append({var.name: var.value()})

    for name, constraint in model.constraints.items():
        print(f"{name}: {constraint.value()}")



    return Response({
        "status": LpStatus[model.status],
        "objective": model.objective.value(),
        "variables": variables


    })
