import json, glob

## Get the name!

def get_name(record):
    for element in record:
      if 'madsrdf:Authority' in element["@type"] and 'madsrdf:PersonalName' in element["@type"]:
        if 'madsrdf:authoritativeLabel' in element:
            return element['madsrdf:authoritativeLabel']        
        
def get_alt_names(record):
    alts = []
    for element in record:
      if "madsrdf:PersonalName" in element["@type"] and "madsrdf:Variant" in element["@type"]:
          if 'madsrdf:variantLabel' in element:
            alts.append(element['madsrdf:variantLabel'])
    return alts

## Discarding Name Title Records

def exclude_name_title(record):
    outcome = "retain"
    for element in record:
        if 'madsrdf:NameTitle' in element["@type"]:
            outcome = "discard"
    return outcome

## Turns generic info into a list of labels and works for several kinds of field

def get_labels(data,uri_list):
    label_output = []
    for entity in data:
        if entity["@id"] in uri_list:
            if "madsrdf:authoritativeLabel" in entity:
                label_output.append(entity["madsrdf:authoritativeLabel"])
            elif "rdfs:label" in entity:
                label_output.append(entity["rdfs:label"])
    return label_output

## Gets the set of URIs and then turns them into labels from data elsewhere in the set  

def get_characteristics(data,field):
  uri_list = []
  for line in data:
    if field in line:
      if type(line[field]) is list:
        for thing in line[field]:
            uri_list.append(thing["@id"])
      else:
         uri_list.append(line[field]["@id"])
  output = get_labels(data,uri_list)
  return output

# Get Citations
# Adding Citation Source because we no longer have Works
def get_citation_data(data):
    citations = []
    for entity in data:
        if "citationNote" in str(entity):
            citations.append(entity["madsrdf:citationNote"])
        if "citationSource" in str(entity):
            citations.append(entity["madsrdf:citationSource"])
    return citations

# checking for a list to be empty or not before writing it into the actual object
# retrieval is done by content element calling the appropriate get function

def retrieve_check_append(combo,label,content):
    if content != []:
        combo[label] = content

# setting up file processing

for file in glob.glob("lc_data/*.txt"):
    print(file)
    with open (file, "r") as fp:
        stuff = []
        output = []
        outfile = file.replace(".txt","_transformed.json")
        for line in fp:
           stuff.append(line.rstrip("\n"))
        for thing in stuff:
            recorddata = json.loads(thing)
            name = get_name(recorddata["@graph"])
            if name != None and exclude_name_title(recorddata["@graph"]) == "retain":
                summation = {"id" : recorddata["@id"], "authorized_name" : name}
                retrieve_check_append(summation,"alt_names",get_alt_names(recorddata["@graph"]))
                retrieve_check_append(summation,"activity", get_characteristics(recorddata["@graph"],'madsrdf:fieldOfActivity'))
                retrieve_check_append(summation,"occupations",get_characteristics(recorddata["@graph"],"madsrdf:occupation"))
                retrieve_check_append(summation,"organizations",get_characteristics(recorddata["@graph"],"madsrdf:organization"))
                retrieve_check_append(summation,"citation_data",get_citation_data(recorddata["@graph"]))
                output.append(summation)
        with open(outfile,'w') as f:
           json.dump(output, f,indent=4,ensure_ascii=False)
