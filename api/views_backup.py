from math import exp

from rest_framework.response import Response
from rest_framework.decorators import api_view
from pulp import LpMinimize, LpMaximize, LpProblem, LpStatus, LpStatusNotSolved, lpSum, LpVariable
from . import data

def getStatus(value):
    if value == LpStatus.OPTIMAL:
        return "Solved"
    elif value == LpStatus.INFEASIBLE:
        return "Infeasible"
    elif value == LpStatus.UNBOUNDED:
        return "Unbounded"
    elif value == LpStatusNotSolved:
        return "Not solved"


def calculateMineral(dmi, pregnancy, lactation, growth, maintenance):
    # print(pregnancy, lactation, growth, maintenance)
    return (pregnancy + lactation + growth + maintenance) / dmi


def breedCoeficient(breed):
    if breed == 1:
        return  1.22
    elif breed == 2:
        return 1.45
    else:
        return 1.37


def getSodiumPregnancyValue(temperature):
    return 0.68 if temperature <= 30 else 3.4


def getCopperPregnancyValue(days_pregnant):
    if days_pregnant < 100:
        return 0.5
    elif days_pregnant < 225:
        return 1.5
    else:
        return 2


def addRoughage(id, percentage, cost):
    roughage = data.roughages[id-1]
    roughage['percentage'] = percentage
    roughage['cost'] = cost
    return roughage


def aggregateRoughageItems(roughages, item):
    total = 0
    for roughage in roughages:
        total += roughage[item] * (roughage['percentage'] / 100)
    return total


def addConcentrate(id, cost):
    concentrate = data.concentrates[id-1]
    concentrate['cost'] = cost
    return concentrate


def getConcentrateItem(id, item):
    concentrate = data.concentrates[id-1]
    return round(concentrate[item],2)


@api_view(['POST'])
def getData(request):

    age = int(request.data['age'])
    live_weight = float(request.data['live_weight'])
    days_pregnant = int(request.data['days_pregnant'])
    days_in_milk = int(request.data['days_in_milk'])
    lactation_number = int(request.data['lactation_number'])
    calf_birth_weight = int(request.data['calf_birth_weight'])
    milk_production = int(request.data['milk_production'])
    milk_fat = float(request.data['milk_fat'])
    body_condition_score = int(request.data['body_condition_score'])
    breed = int(request.data['breed'])
    mature_weight = int(request.data['mature_bw'])
    weight_gain = int(request.data['weight_gain'])
    atmospheric_temperature = float(request.data['atmospheric_temperature'])
    roughages = []
    concentrates = []


    # Dry Matter Intake (DMI)
    week_of_lactation = days_in_milk/7
    fat_corrected_milk = (0.4 * milk_production) + (15 * ((milk_fat / 100) * milk_production))
    dmi = (0.372 * fat_corrected_milk) + ((0.0968 * pow(live_weight, 0.75)) * (1 - exp(-0.192 * (week_of_lactation + 3.67))))

    # Energy
    net_energy_for_maintenance = 0.08 * pow(live_weight, 0.75)
    net_energy_for_lactation = (0.36 + (0.0969 * milk_fat)) * milk_production
    net_energy_for_pregnancy = ((0.00318 * days_pregnant - 0.0352) * (calf_birth_weight/ 45)) / 0.218
    net_energy_for_growth_and_replenishment = (net_energy_for_maintenance + net_energy_for_lactation + net_energy_for_pregnancy) * 0.05
    energy_concentration = (net_energy_for_maintenance + net_energy_for_lactation + net_energy_for_pregnancy + net_energy_for_growth_and_replenishment) / dmi

    # Minerals
    # 1. Calcium
    calcium = calculateMineral(
        dmi,
        pregnancy=(0.02456 * exp(0.05581 - (0.00007 * days_pregnant)) * days_pregnant) - (0.02456 * exp(0.05581 - 0.00007 * (days_pregnant - 1) * (days_pregnant - 1)) * (days_pregnant-1)),
        lactation=milk_production * breedCoeficient(breed),
        growth=(9.83 * pow(mature_weight, 0.22) * pow(live_weight, -0.22) * weight_gain),
        maintenance=0.031 * live_weight
    )

    # 2. Phosphorus
    phosphorus = calculateMineral(
        dmi,
        pregnancy=(0.02743 * exp(0.05527 - (0.000075 * days_pregnant)) * days_pregnant) - (0.02743 * exp(0.05527 - 0.000075 *(days_pregnant - 1) * (days_pregnant - 1)) * (days_pregnant - 1)),
        lactation=0.9 * milk_production,
        growth=(1.2 + (4.635 * pow(mature_weight, 0.22) * pow(live_weight, 0.22))) * weight_gain,
        maintenance=(1 * dmi) + (0.002 * live_weight)
    )

    # 3. Sodium
    sodium = calculateMineral(
        dmi,
        pregnancy=getSodiumPregnancyValue(atmospheric_temperature),
        lactation=0.63 * milk_production,
        growth=1.4 * weight_gain,
        maintenance=0.038 * live_weight
    )

    # 4. Chlorine
    chlorine = calculateMineral(
        dmi,
        pregnancy=1,
        lactation=1.15 * milk_production,
        growth=1 * weight_gain,
        maintenance=2.25 * (live_weight / 100)
    )

    # 5. Potassium
    potassium = calculateMineral(
        dmi,
        pregnancy=1.027,
        lactation=1.5 * milk_production,
        growth=1.6 * weight_gain,
        maintenance=(6.1 * dmi) + (0.038 * live_weight)
    )

    # 6. Magnesium
    magnesium = calculateMineral(
        dmi,
        pregnancy=0.33 * days_pregnant,
        lactation=0.15 * milk_production,
        growth=0.45 * (weight_gain / 0.96),
        maintenance=0.003 * live_weight
    )

    # 7. Sulphur
    sulphur = (2 * dmi) / dmi

    # 8. Cobalt
    cobalt = (0.11 * dmi)

    # 9. Copper
    copper = calculateMineral(
        dmi,
        pregnancy=getCopperPregnancyValue(days_pregnant),
        lactation=0.15 * milk_production,
        growth=1.15 * (weight_gain / 0.96),
        maintenance=0.0071 * live_weight
    )

    # 10. Iodine
    iodine = (1.5 * (live_weight / 100)) / dmi

    # 11. Iron
    iron = calculateMineral(
        dmi,
        pregnancy=18 if days_pregnant > 190 else 0,
        lactation=1 * milk_production,
        growth=34 * (weight_gain / 0.96),
        maintenance=0
    )

    # 12. Manganese
    manganese = calculateMineral(
        dmi,
        pregnancy=0.3 if days_pregnant > 190 else 0,
        lactation=0.03 * milk_production,
        growth=0.7 * (weight_gain / 0.96),
        maintenance=0.002 * live_weight
    )

    # 13. Selenium
    selenium = 0.3 * dmi

    # 14. Zinc
    zinc = calculateMineral(
        dmi,
        pregnancy=12 if days_pregnant > 190 else 0,
        lactation=4 * milk_production,
        growth=24 * (weight_gain / 0.96),
        maintenance=(0.033 * live_weight) + (0.012 * live_weight)
    )

    # 15. Vitamin A
    vitamin_a = (0.11 * live_weight) / dmi

    # 16. Vitamin D
    vitamin_d = (0.03 * live_weight) / dmi

    # 17. Vitamin E
    vitamin_e = (0.8 * live_weight) / dmi

    # Dairy Premix
    dairy_premix = ((120 + (15 * milk_production)) / (1000 * dmi)) * 100

    # Selecting Roughages
    for var in request.data['roughages']:
        roughages.append(addRoughage(var['id'], var['percentage'], var['cost']))

    roughage_combined_ndf = aggregateRoughageItems(roughages,"ndf")
    roughage_combined_cp = aggregateRoughageItems(roughages,"cp")
    roughage_combined_cost = aggregateRoughageItems(roughages,"cost")
    roughage_combined_energy = aggregateRoughageItems(roughages,"net_energy")
    roughage_dmi = (1.2 * 0.65 * live_weight) / roughage_combined_ndf
    roughage_proportion = (roughage_dmi / dmi) * 100

    concentrate_dmi = dmi - roughage_dmi
    concentrate_proportion = (concentrate_dmi / dmi) * 100

    # Selecting Concentrates
    for var in request.data['concentrates']:
        concentrates.append(addConcentrate(var['id'], var['cost']))

    print(roughage_proportion, concentrate_proportion, getConcentrateItem(1, 'cp'))

    # return Response({
    #     "dmi": dmi,
    #     "energy_concentration": energy_concentration,
    #     "dairy_premix": dairy_premix,
    #     "calcium": calcium,
    #     "phosphorus": phosphorus,
    #     "sodium": sodium,
    #     "chlorine": chlorine,
    #     "potassium": potassium,
    #     "magnesium": magnesium,
    #     "sulphur": sulphur,
    #     "cobalt": cobalt,
    #     "copper": copper,
    #     "iodine": iodine,
    #     "iron": iron,
    #     "manganese": manganese,
    #     "selenium": selenium,
    #     "zinc": zinc,
    #     "vitamin_a": vitamin_a,
    #     "vitamin_d": vitamin_d,
    #     "vitamin_e": vitamin_e,
    #
    # })




    model = LpProblem(name="small-problem", sense=LpMinimize)

    a = LpVariable(name="Roughage Proportion", lowBound=round(roughage_proportion,2)/100, upBound=round(roughage_proportion,2)/100)
    b = LpVariable(name="Maize Bran", lowBound=0, upBound=1 if getConcentrateItem(1, 'cost') > 0 else 0)
    c = LpVariable(name="Soy Bean Cake EE", lowBound=0, upBound=1 if getConcentrateItem(2, 'cost') > 0 else 0)
    d = LpVariable(name="Soy Bean Meal Full Fat", lowBound=0, upBound=1 if getConcentrateItem(3, 'cost') > 0 else 0)
    e = LpVariable(name="Sunflower Cake", lowBound=0, upBound=1 if getConcentrateItem(4, 'cost') > 0 else 0)
    f = LpVariable(name="Brewers Grain, Dehydrated", lowBound=0, upBound=1 if getConcentrateItem(5, 'cost') > 0 else 0)
    g = LpVariable(name="Brewers grain, Fresh", lowBound=0, upBound=1 if getConcentrateItem(6, 'cost') > 0 else 0)
    h = LpVariable(name="Cotton Seed meal, Dehulling, ME", lowBound=0, upBound=0.03 if getConcentrateItem(7, 'cost') > 0 else 0)
    i = LpVariable(name="Cotton Seed meal, No Dehulling, No Extraction", lowBound=0, upBound=0.03 if getConcentrateItem(8, 'cost') > 0 else 0)
    j = LpVariable(name="Cotton Seed meal, Dehulling, SE", lowBound=0, upBound=0.03 if getConcentrateItem(9, 'cost') > 0 else 0)
    k = LpVariable(name="Rice bran", lowBound=0, upBound=1 if getConcentrateItem(10, 'cost') > 0 else 0)
    l = LpVariable(name="Baobab Seed", lowBound=0, upBound=1 if getConcentrateItem(11, 'cost') > 0 else 0)
    m = LpVariable(name="Urea (N)", lowBound=0, upBound=0.001 if getConcentrateItem(12, 'cost') > 0 else 0)
    n = LpVariable(name="Poultry Litter", lowBound=0, upBound=0.05 if getConcentrateItem(13, 'cost') > 0 else 0)
    o = LpVariable(name="Molasses", lowBound=0, upBound=0.03 if getConcentrateItem(14, 'cost') > 0 else 0)
    p = LpVariable(name="Dairy Premix", lowBound=round(dairy_premix,2)/100, upBound=round(dairy_premix,2)/100)
    q = LpVariable(name="MCP", lowBound=0, upBound=0.015 if getConcentrateItem(16, 'cost') > 0 else 0)
    r = LpVariable(name="Salt", lowBound=0.01, upBound=1)
    s = LpVariable(name="Sodium Bicarbonate", lowBound=0,upBound=0.01 if getConcentrateItem(18, 'cost') > 0 else 0)
    t = LpVariable(name="Water", lowBound=0, upBound=1 if getConcentrateItem(19, 'cost') > 0 else 0)

    model += (a + b + c + d + e + f + g + h + i + j + k + l + m + n + o + p + q + r + s + t == 1, 'tally')

    model += (a * round(roughage_combined_cp,2) +
              b * getConcentrateItem(1, 'cp') +
              c * getConcentrateItem(2, 'cp') +
              d * getConcentrateItem(3, 'cp') +
              + e * getConcentrateItem(4, 'cp') +
              f * getConcentrateItem(5, 'cp') +
              g * getConcentrateItem(6, 'cp') +
              h * getConcentrateItem(7, 'cp') +
              i * getConcentrateItem(8, 'cp') +
              j * getConcentrateItem(9, 'cp') +
              k * getConcentrateItem(10, 'cp') +
              l * getConcentrateItem(11, 'cp') +
              m * getConcentrateItem(12, 'cp') +
              n * getConcentrateItem(13, 'cp') +
              o * getConcentrateItem(14, 'cp') +
              p * getConcentrateItem(15, 'cp') +
              q * getConcentrateItem(16, 'cp') +
              r * getConcentrateItem(17, 'cp') +
              s * getConcentrateItem(18, 'cp') +
              t * getConcentrateItem(19, 'cp')
              >= 16, 'crude_protein_lower')
    model += (a * round(roughage_combined_cp,2) +
              b * getConcentrateItem(1, 'cp') +
              c * getConcentrateItem(2, 'cp') +
              d * getConcentrateItem(3, 'cp') +
              e * getConcentrateItem(4, 'cp') +
              f * getConcentrateItem(5, 'cp') +
              g * getConcentrateItem(6, 'cp') +
              h * getConcentrateItem(7, 'cp') +
              i * getConcentrateItem(8, 'cp') +
              j * getConcentrateItem(9, 'cp') +
              k * getConcentrateItem(10, 'cp') +
              l * getConcentrateItem(11, 'cp') +
              m * getConcentrateItem(12, 'cp') +
              n * getConcentrateItem(13, 'cp') +
              o * getConcentrateItem(14, 'cp') +
              p * getConcentrateItem(15, 'cp') +
              q * getConcentrateItem(16, 'cp') +
              r * getConcentrateItem(17, 'cp') +
              s * getConcentrateItem(18, 'cp') +
              t * getConcentrateItem(19, 'cp')
              <= 23, 'crude_protein_upper')
    model += (a * round(roughage_combined_ndf,2) +
              b * getConcentrateItem(1, 'ndf') +
              c * getConcentrateItem(2, 'ndf') +
              d * getConcentrateItem(3, 'ndf') +
              e * getConcentrateItem(4, 'ndf') +
              f * getConcentrateItem(5, 'ndf') +
              g * getConcentrateItem(6, 'ndf') +
              h * getConcentrateItem(7, 'ndf') +
              i * getConcentrateItem(8, 'ndf') +
              j * getConcentrateItem(9, 'ndf') +
              k * getConcentrateItem(10, 'ndf') +
              l * getConcentrateItem(11, 'ndf') +
              m * getConcentrateItem(12, 'ndf') +
              n * getConcentrateItem(13, 'ndf') +
              o * getConcentrateItem(14, 'ndf') +
              p * getConcentrateItem(15, 'ndf') +
              q * getConcentrateItem(16, 'ndf') +
              r * getConcentrateItem(17, 'ndf') +
              s * getConcentrateItem(18, 'ndf') +
              t * getConcentrateItem(19, 'ndf')
              >= 20, 'ndf_lower')
    model += (a * round(roughage_combined_ndf,2) +
              b * getConcentrateItem(1, 'ndf') +
              c * getConcentrateItem(2, 'ndf') +
              d * getConcentrateItem(3, 'ndf') +
              e * getConcentrateItem(4, 'ndf') +
              f * getConcentrateItem(5, 'ndf') +
              g * getConcentrateItem(6, 'ndf') +
              h * getConcentrateItem(7, 'ndf') +
              i * getConcentrateItem(8, 'ndf') +
              j * getConcentrateItem(9, 'ndf') +
              k * getConcentrateItem(10, 'ndf') +
              l * getConcentrateItem(11, 'ndf') +
              m * getConcentrateItem(12, 'ndf') +
              n * getConcentrateItem(13, 'ndf') +
              o * getConcentrateItem(14, 'ndf') +
              p * getConcentrateItem(15, 'ndf') +
              q * getConcentrateItem(16, 'ndf') +
              r * getConcentrateItem(17, 'ndf') +
              s * getConcentrateItem(18, 'ndf') +
              t * getConcentrateItem(19, 'ndf')
              <= 40, 'ndf_upper')
    model += (a * round(roughage_combined_energy,2) +
              b * getConcentrateItem(1, 'net_energy') +
              c * getConcentrateItem(2, 'net_energy') +
              d * getConcentrateItem(3, 'net_energy') +
              e * getConcentrateItem(4, 'net_energy') +
              f * getConcentrateItem(5, 'net_energy') +
              g * getConcentrateItem(6, 'net_energy') +
              h * getConcentrateItem(7, 'net_energy') +
              i * getConcentrateItem(8, 'net_energy') +
              j * getConcentrateItem(9, 'net_energy') +
              k * getConcentrateItem(10, 'net_energy') +
              l * getConcentrateItem(11, 'net_energy') +
              m * getConcentrateItem(12, 'net_energy') +
              n * getConcentrateItem(13, 'net_energy') +
              o * getConcentrateItem(14, 'net_energy') +
              p * getConcentrateItem(15, 'net_energy') +
              q * getConcentrateItem(16, 'net_energy') +
              r * getConcentrateItem(17, 'net_energy') +
              s * getConcentrateItem(18, 'net_energy') +
              t * getConcentrateItem(19, 'net_energy')
              >= round(energy_concentration,2) * 0.95, 'net_energy_lower')
    model += (a * round(roughage_combined_energy,2) +
              b * getConcentrateItem(1, 'net_energy') +
              c * getConcentrateItem(2, 'net_energy') +
              d * getConcentrateItem(3, 'net_energy') +
              e * getConcentrateItem(4, 'net_energy') +
              f * getConcentrateItem(5, 'net_energy') +
              g * getConcentrateItem(6, 'net_energy') +
              h * getConcentrateItem(7, 'net_energy') +
              i * getConcentrateItem(8, 'net_energy') +
              j * getConcentrateItem(9, 'net_energy') +
              k * getConcentrateItem(10, 'net_energy') +
              l * getConcentrateItem(11, 'net_energy') +
              m * getConcentrateItem(12, 'net_energy') +
              n * getConcentrateItem(13, 'net_energy') +
              o * getConcentrateItem(14, 'net_energy') +
              p * getConcentrateItem(15, 'net_energy') +
              q * getConcentrateItem(16, 'net_energy') +
              r * getConcentrateItem(17, 'net_energy') +
              s * getConcentrateItem(18, 'net_energy') +
              t * getConcentrateItem(19, 'net_energy')
              <= round(energy_concentration,2), 'net_energy_upper')

    objective = lpSum([
        a * roughage_combined_cost,
        b * getConcentrateItem(1, 'cost'),
        c * getConcentrateItem(2, 'cost'),
        d * getConcentrateItem(3, 'cost'),
        e * getConcentrateItem(4, 'cost'),
        f * getConcentrateItem(5, 'cost'),
        g * getConcentrateItem(6, 'cost'),
        h * getConcentrateItem(7, 'cost'),
        i * getConcentrateItem(8, 'cost'),
        j * getConcentrateItem(9, 'cost'),
        k * getConcentrateItem(10, 'cost'),
        l * getConcentrateItem(11, 'cost'),
        m * getConcentrateItem(12, 'cost'),
        n * getConcentrateItem(13, 'cost'),
        o * getConcentrateItem(14, 'cost'),
        p * getConcentrateItem(15, 'cost'),
        q * getConcentrateItem(16, 'cost'),
        r * getConcentrateItem(17, 'cost'),
        s * getConcentrateItem(18, 'cost'),
        t * getConcentrateItem(19, 'cost')
    ])

    model += objective

    print(model)

    status = model.solve()

    print(f"status: {model.status}, {LpStatus[model.status]}")
    print(f"objective: {model.objective.value()}")

    roughages_results = []
    concentrates_results = []

    if status == 1:
        for roughage in roughages:
            roughages_results.append({
                "name": roughage['name'],
                "value": roughage['percentage'],
                "weight": round((roughage_proportion/100) * dmi * (roughage['percentage']/100), 2)
            })

        for var in model.variables():
            if var.value() > 0 :
                concentrates_results.append({
                    "name": var.name,
                    "value": round(var.value() * 100, 2),
                    "weight": round(var.value() * dmi, 2)
                })


    for name, constraint in model.constraints.items():
        print(f"{name}: {constraint.value()}")

    return Response({
        "status": model.status,
        "status_message": LpStatus[model.status],
        # "milk_production": milk_production,
        "objective": round(model.objective.value(), 2),
        "roughages": roughages_results,
        "concentrates": concentrates_results,
        "dmi": dmi,
        "energy_concentration": energy_concentration,
        "roughage_combined_energy":roughage_combined_energy,
        "roughage_combined_cp":roughage_combined_cp,
        "roughage_combined_ndf":roughage_combined_ndf,
        "roughage_proportion":roughage_proportion,
        # "dairy_premix": dairy_premix,
        # "calcium": calcium,
        # "phosphorus": phosphorus,
        # "sodium": sodium,
        # "chlorine": chlorine,
        # "potassium": potassium,
        # "magnesium": magnesium,
        # "sulphur": sulphur,
        # "cobalt": cobalt,
        # "copper": copper,
        # "iodine": iodine,
        # "iron": iron,
        # "manganese": manganese,
        # "selenium": selenium,
        # "zinc": zinc,
        # "vitamin_a": vitamin_a,
        # "vitamin_d": vitamin_d,
        # "vitamin_e": vitamin_e,
    })
