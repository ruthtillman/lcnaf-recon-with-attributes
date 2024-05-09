import json, glob, re
from fuzzywuzzy import fuzz
from itertools import chain

file_name = "sample/sample_local.json" # Your starter records
outfile = "batch_one_results.json" # Your results file.

# This tests names to see if there are any middle segments. Importantly, it is NOT foolproof and does not perform well for people with 4 or more unhyphenated names. It's just an attempt to get data any way one can.

def augment_inversion(inverted_name,full_name):
    name_parts = inverted_name.split(", ")
    working_name = full_name.replace(name_parts[1],"",1)
    working_name = working_name[:working_name.rfind(name_parts[0])].strip()
    return working_name

# Tests and scores potential alt names. It could be incorporated with the primary name, but it was developed secondarily to handle iterating through the alt names as a list and was not revisited because it worked.

def get_alt_name_scores(entry,authorized_names):
    inverted = entry["inverted_name"]
    regular_name = entry["name"]
    scores = [] # Recording scores so that max can be tested
    for name in authorized_names:
        scores.append(fuzz.ratio(name,inverted))
    if max(scores) < 90: # Max tests the highest value in the list
        augmentation = augment_inversion(inverted,regular_name)
        if augmentation != '':
            if len(augmentation) == 1:
                augmentation = augmentation + "."
            additional_name = inverted + " " + augmentation
            for name in authorized_names:
                scores.append(fuzz.ratio(name,additional_name))
                if max(scores) < 90:
                    if len(augmentation.rstrip(".")) > 1:
                        initial = augmentation[0].upper() + "."
                        yet_another_name = inverted + " " + initial
                        for name in authorized_names:
                            scores.append(fuzz.ratio(name,yet_another_name))
                        return max(scores)
                    elif len(augmentation) <= 2: ## Note, this whole section should be removed for people who cannot provide something like an institutional identifier which contains people's initials. The access_id being referred to here is something like rkt6.
                        if re.match("[a-z]{3}",entry["access_id"][0:3]) and entry["access_id"][1] != "x": 
                            yet_another_name = inverted + " " + entry["access_id"][1].upper() + "."
                            for name in authorized_names:
                                scores.append(fuzz.ratio(name,yet_another_name))
                            return max(scores)
                        else:
                            return max(scores)
                    else:
                        return max(scores)
                else:
                    return max(scores)
        else:
            return max(scores)
    else:
        return max(scores)
    

def get_name_scores(entry,record):
    id = entry["access_id"] # s above, this variable and its use below should be removed if you don't have some kind of identifier which can be used to identify potential middle intiials.
    inverted = entry["inverted_name"]
    regular_name = entry["name"]
    authorized = [record['authorized_name'].rstrip(" ,0123456789-?")] # This strips the dates but does not handle parentheticals. This could be improved.
    if "alt_names" in record:
        for name in record["alt_names"]:
            authorized.append(name.rstrip(" ,0123456789-?"))
    basic_authorized = fuzz.ratio(authorized[0],inverted)
    if basic_authorized < 90:
        augmentation = augment_inversion(inverted,regular_name)
        if augmentation != '':
            if len(augmentation) == 1:
                augmentation = augmentation + "."
            additional_name = inverted + " " + augmentation
            augmented = fuzz.ratio(authorized[0],additional_name)
            if augmented > 89:
                match_data = {"basic_ratio" :basic_authorized, "augmented_ratio" : augmented}
            if len(augmentation.rstrip(".")) > 1 and augmented != 100:
                initial = augmentation[0].upper() + "."
                yet_another_name = inverted + " " + initial
                ynn = fuzz.ratio(authorized[0],yet_another_name)
                match_data = {"basic_ratio" :basic_authorized, "augmented_ratio" : augmented, "ynn" : ynn}
            if len(augmentation) <= 2 and augmented != 100:
                match_data = {"basic_ratio" :basic_authorized, "augmented_ratio" : augmented}
        elif augmentation == '':
            if re.match("[a-z]{3}",id[0:3]) and id[1] != "x":
                yet_another_name = inverted + " " + id[1].upper() + "."
                ynn = fuzz.ratio(authorized[0],yet_another_name)
                match_data = {"basic_ratio" :basic_authorized, "ynn" : ynn}
            else:
                match_data = {"basic_ratio" :basic_authorized}
    else:
        match_data = {"basic_ratio" :basic_authorized}
    best_match = max(list(match_data.values()))
    if best_match < 90 and len(authorized) > 1:
        second_best_match = get_alt_name_scores(entry,authorized[1:])
        best_match = max([best_match,second_best_match]) # now best match is whichever of the two is higher
    match_outcome = {"id" : id, "local_name" : regular_name, "lc_name":record['authorized_name'], "best_match" : best_match}
    return match_outcome

# This tests the organization field and citation data fields for your institutional value. Review values and replace with your own.

def check_for_affiliation(record):
    penn_state = []
    if "organization" in record:
        if "Penn State" in str(record["organization"]) or "Pennsylvania State" in str(record["organization"]) or "School of Humanities (Harrisburg)" in str(record["organization"]):
            penn_state.append("organization")
    if "citation_data" in record:
        if "Penn State" in str(record["citation_data"]) or "Pennsylvania State" in str(record["citation_data"]) or "PennState" in str(record["citation_data"]) or "State College, PA" in str(record["citation_data"]) or "Penn. State" in str(record["citation_data"]):
            penn_state.append("citation")
    return penn_state

# Checks the occupation field for the values determined to be of use in identifying faculty.

def check_occupation(record):
    teachers = "False"
    if "occupations" in record:
        if "teachers" in str(record["occupations"]) or "University and college faculty members" in str(record["occupations"]) or "Librarian" in str(record["occupations"]):
            teachers = "True"
    return teachers

## Looks for a person's field of activity in their department name. Splits field of activity by -- if needed. Checks for the full PSU department name in the citation.

def check_activity(record,entry):
    field = []
    if "activity" in record and "dept_name" in entry:
        if entry["dept_name"] is not None:
            for activity in record["activity"]:
                for act in activity.split("--"):
                    if act is not None:
                        if act.lower() in entry["dept_name"].lower():
                            field.append("activity")
    if "dept_name" in entry and "citation_data" in record:
        if entry["dept_name"] is not None:
            if entry["dept_name"].lower() in str(record["citation_data"]).lower():
                field.append("citation")
    return field

## Creates a set of comparatively normalized university names from faculty-entered data.

def create_university_if_needed(school):
    school.replace("  "," ") ## fix the one case with double space
    if school[0:3].lower() == "the": #remove "The " from the front
        school = school[4:]
    if "Univ." in school:  ## now manage all the turning it into universities
        school = school.replace("Univ.","University")
    elif "Univ " in school:
        school = school.replace("Univ","University")
    elif "U of" in school:
        school = school.replace("U of","University of")
    return school


# From a more normalized university name, creates variants to match what catalogers do in citations.
def create_variants(school):
    variant_list = [school]
    variant_list = list(chain(variant_list,[school.replace("University","Univ"),school.replace("University","Univ.")]))
    if school.startswith("University of"):
        variant_list = list(chain(variant_list,[school.replace("University of","U of"),school.replace("University of","U. of")]))
    elif school.endswith("University"):
        variant_list = list(chain(variant_list,[school.replace("University","U")]))
    return variant_list

# Takes a school name and applies functions above to create a variety of values which can be used in testing.
def create_edu_history(school):
    school = create_university_if_needed(school)
    variants = list(set(create_variants(school))) # makes it unique values only
    return(school,variants)

# Performs the tests. Assumes educational history "hist" as a list of text values. It tests the most likely form against organization. Then it tests for all values in the citation.

def check_education_history(hist,record):
    results = []
    for school in hist:
        working_data = create_edu_history(school)
        if "organizations" in record and "organization" not in results:
            if working_data[0] in str(record["organizations"]):
                results.append("organization")
        for school in working_data[1]:
            if "citation" not in results and "citation_data" in record:
                if school.lower() in str(record["citation_data"]).lower(): #lowercase!
                    results.append("citation")
    return results

with open(file_name, "r") as myJSON:
    names = json.loads(myJSON.read())

working_list = []
for entry in names:
    for file in glob.glob("lc_data/*.json"): # your directory containing the transformed LC names as JSON
        with open (file, "r") as myJSON:
            recorddata = json.loads(myJSON.read())
            for record in recorddata:
                if type(record["authorized_name"]) is not list:
                    data = get_name_scores(entry,record)
                    if data["best_match"] > 89 and data["best_match"] < 101: # Match testing 90-100
                        data["url"] = "http://id.loc.gov" + record["id"]
                        affiliation = check_for_affiliation(record)
                        if affiliation != []:
                            data["affiliation"] = affiliation
                        if "organizations" in record:
                            data["lc_organizations"] = record["organizations"]
                        if check_occupation(record) == "True":
                            data["occupation_match"] = "True"
                        if "occupations" in record:
                            data["lc_occupations"] = record["occupations"] # get actual data
                        activity = check_activity(record,entry)
                        if activity != []:
                            data["activity_match"] = activity
                        if "dept_name" in entry:
                            data["local_organization"] = entry["dept_name"]
                        if "activity" in record:
                            data["lc_activity"] = record["activity"]
                        if "education_history" in entry:
                            data["local_education"] = entry["education_history"]
                        if type(entry['education_history']) is list:
                            education = check_education_history(entry['education_history'],record)
                            if education != []:
                                data["education_match"] = education
                        if "citation_data" in record:
                            data["lc_citation_data"] = record["citation_data"]
                        if data.get("activity_match") is not None or data.get("education_match") is not None or data.get("affiliation") is not None: # this runs a whole test because we could have matched on a decent name but not on anything else. One of these has to contain data for it to be appended. This originally contained occupation matches, but these were found to be such a poor indicator in determining an accurate match that they were removed. Occuption data that exists will still be included in the results for review along with information about whether there's an occupation match.
                            working_list.append(data)
                        with open(outfile,'w') as f:
                            json.dump(working_list, f,indent=3,ensure_ascii=False)

