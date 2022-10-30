from bs4 import BeautifulSoup as soup
from urllib.request import urlopen
from copy import deepcopy
import re
from json import load
from collections import OrderedDict
import ssl


try:
    # see if there is an external info file
    with open("./school_subject.json", "r") as file:
        subject_to_school = load(file)
except:
    subject_to_school = {
        "HLTH": "DSTO",
        "ENVR": "IPO",
        "SUST": "IPO",
        "ENTR": "JS",
        "RMBI": "JS",
        "ACCT": "SBM",
        "ECON": "SBM",
        "FINA": "SBM",
        "ISOM": "SBM",
        "MARK": "SBM",
        "MGMT": "SBM",
        "BIEN": "SENG",
        "BMED": "SENG",
        "CENG": "SENG",
        "CIVL": "SENG",
        "COMP": "SENG",
        "ELEC": "SENG",
        "ENGG": "SENG",
        "IEDA": "SENG",
        "IELM": "SENG",
        "ISDN": "SENG",
        "MECH": "SENG",
        "HART": "SHSS",
        "HUMA": "SHSS",
        "LANG": "SHSS",
        "SHSS": "SHSS",
        "SOSC": "SHSS",
        "CHEM": "SSCI",
        "LIFS": "SSCI",
        "MATH": "SSCI",
        "OCES": "SSCI",
        "PHYS": "SSCI",
        "SCIE": "SSCI",
        "PPOL": "IPO"
    }

try:
    # see if there is an external info file
    with open("./common_core_order.json", "r") as file:
        common_core_order = {cc:i for i, cc in enumerate(load(file))}
except:
    common_core_order = {
        "H-SSC": 0,
        "SA-SSC": 1,
        "S&T-SSC": 2,
        "QR-SSC": 3,
        "C-Comm-SSC": 4,
        "Arts-SSC": 5,
        "H": 6,
        "SA": 7,
        "S&T": 8,
        "QR": 9,
        "C-Comm": 10,
        "E-Comm": 11,
        "Arts": 12,
        "HLTH": 13,
    }

def getHtml(url):
    import requests
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    resp = requests.get(url, verify=False)
    # print(resp.content.decode("utf-8") )
    # with urlopen(url, context=ctx) as page:
    return soup(resp.content.decode("utf-8"), "html.parser")

def getInstructors(html):
    parse_instructors = []
    instructors = html.findAll("a") # instructor shall have a href link to its only class page
    if instructors:
        for instructor in instructors:
            parse_instructors.append(instructor.text)
    else: # some do not have href, e.g. TBA
        parse_instructors.append(html.text)
    return parse_instructors

course_header = re.compile("(\w{0,10}) (\w{0,10}) - (.+) \((\d) unit(s{0,1})\)")
cc_area = re.compile("Common Core \((.{0,10})\)")
section_col = re.compile("(\w+) \((\d+)\)")
number = re.compile("(\d+)")
def parseCourse(course):
    parse_course = {
        "Common Core Area": None,
        "School": None,
        "Subject Area": None,
        "Course Number": None,
        "Course Title": None,
        "Units": None,
        "Instructor": None,
        "Section": None,
        "Quota for Each Section": None,
        "Total Quota": None
    }
    try:
        parse_header = course_header.findall(course.find("h2").text)[0]
        parse_course["Subject Area"], parse_course["Course Number"], parse_course["Course Title"], parse_course["Units"], _ = parse_header
        parse_course["School"] = subject_to_school[parse_course["Subject Area"]]
        parse_course["Common Core Area"] = cc_area.findall(course.find("div", {"courseattr"}).text)

        parse_course["Section"] = []
        sections = course.find("table", {"sections"}).findAll("tr")[1:] # get all the rows (sections), except the column title
        # print(course.find("h2").text)
        for section in sections:
            info = section.findAll("td")
            if len(info) <= 3:
                """
                The row does not have complete infomation
                i.e. it is the same section as the last one, but with different time slot
                info[0]: Time,
                info[1]: Room,
                info[2]: Instructor
                """
                newSection = parse_course["Section"][-1]
                newSection["Time"].append(info[0].text)

                if newSection["Room"][0] != info[1].text: # if they are of different room, add the new room to the list
                    newSection["Room"].append(info[1].text)

                newInstructors = getInstructors(info[2])
                if newSection["Instructor"] != newInstructors: # if they have different instructor, add the new instructor to the list
                    newSection["Instructor"] += newInstructors
            else:
                """
                The row have complete information
                i.e. it is a new section
                info[0]: Section,
                info[1]: Time,
                info[2]: Room,
                info[3]: Instructor,
                info[4]: Quota,
                info[5]: Enrol,
                info[6]: Avail,
                info[7]: Wait
                """
                newSection = {}

                newSection["Section"], newSection["Section Code"] = section_col.findall(info[0].text)[0]
                newSection["Time"] = [info[1].text]
                newSection["Room"] = [info[2].text]
                newSection["Instructor"] = getInstructors(info[3])
                newSection["Quota"] = int(number.findall(info[4].text)[0])
                newSection["Enrol"] = int(number.findall(info[5].text)[0])
                newSection["Available"] = int(number.findall(info[6].text)[0])
                newSection["Wait"] = int(number.findall(info[7].text)[0])

                parse_course["Section"].append(newSection)

        return parse_course, True, None
    except Exception as e:
        return parse_course, False, e

def parseToDict(section, info):
    cat = OrderedDict()
    for s, i in zip(section, info):
        if not cat.get(i):
            cat[i] = []
        cat[i].append(s)
    return cat

getSuffix = re.compile("[a-zA-Z]{1,5}(\d{1,5})")
def parseListToStr(l, seperator):
    # get the number of the section, assume that sections number are in order
    # print(l)
    nums, unknown = [], []
    for i in l:
        try:
            nums.append(int(getSuffix.findall(i)[0]))
        except: # weird things happen, just ignore it first
            unknown.append(i)

    string = ""
    start = 0
    # if there are only a single section, just add that section, otherwise add the start section to the end section


    renderStr = lambda i: seperator + (l[start] if start == i-1 else l[start] + " - " + l[i-1])

    for i in range(1, len(nums)):
        if nums[i-1] + 1 != nums[i]:
            string += renderStr(i)
            start = i

    if len(nums): # can be 0 if all input is weird
        string += renderStr(len(nums)) # render the final section

    # just add back the unknowns to the end
    for i in unknown:
        string += seperator + i

    string = string.replace(seperator, "", 1) # remove the first unwanted seperator

    return string

getPrefix = re.compile("([a-zA-Z]{1,5})(\d{1,5}|X)")
def formatCourse(course):
    try:
        error = None
        # Clean up the "Common Core Area" and turn it into string
        ssc_cc = [s.replace("SSC-", "") for s in course["Common Core Area"] if "SSC-" in s] # find all ssc
        # if there is ssc, delete the non-ssc one (Note: Here has an assumption that ssc can also satisfy non-ssc in the same area)
        cc = list(set(course["Common Core Area"]) - set(ssc_cc)) if ssc_cc else course["Common Core Area"]
        # turn "SSC-XXX" to "XXX-SSC"
        for i in range(len(cc)):
            if "SSC-" in cc[i]:
                cc[i] = cc[i][4:] + "-SSC"
        # Sort the common core order for cross-list cc subject
        if len(cc) > 1: cc.sort(key=lambda cc: common_core_order[cc])
        # create the string from the given cc area

        """31/10/2022 Update:

        After the above processing, it is possible the same course common area appears for twice.

        For example: E-Comm + E-Comm

        To solve this problem, I convert it to set from list (again).
        """
        cc = set(cc)
        course["Common Core Area"] = " + ".join(cc)

        # get the section prefix, e.g. "L" in "L1", "T" in "T1"
        # section_prefix = [getPrefix.findall(sec["Section"])[0] for sec in course["Section"]]
        section_prefix = []
        # print(course)
        # print(f"Course: {course['Subject Area']}{course['Course Number']}, area: {course['Common Core Area']}")
        # if len(course['Section']) < 10:
        #     print(course['Section'])
        # else:
        #     print("(omitted since too much)")
        for sec in course["Section"]:
            try:
                section_prefix.append(getPrefix.findall(sec["Section"])[0][0])
            except Exception as e: # something weird happen
                error = e
                if len(section_prefix) and section_prefix[-1] in sec["Section"]: # if it matches with the last detected prefix, append it to the list
                    section_prefix.append(section_prefix[-1][0])

        # Assume that we only care about data in the first type of section as it can provide sufficient info(e.g. instructor, quota, etc.)
        # e.g. only care about data in the lecture section, and thus the turtorial section can be discarded
        num_section = section_prefix.count(section_prefix[0])

        # print(f"prefix list: {section_prefix}, count = {num_section}")


        course["Section"] = course["Section"][:num_section] # discard all the unwanted section

        section = [s["Section"] for s in course["Section"]]
        # print(section)
        instructor = [s["Instructor"] for s in course["Section"]]
        quota = [s["Quota"] for s in course["Section"]]

        if instructor.count(instructor[0]) == len(instructor): # if instructor in all sections are the same
            course["Instructor"] = "\n".join(instructor[0])
        else:
            instructor_hash = [str(i) for i in instructor] # turn list into string to make it hashable
            cat = parseToDict(section, instructor_hash)
            course["Instructor"] = ""
            for key, value in cat.items():
                course["Instructor"] += parseListToStr(value, ", ") + ": " + "\n".join(eval(key)) + "\n"
            course["Instructor"] = course["Instructor"][:-1] # remove the last "\n"

        if quota.count(quota[0]) == len(quota): # if quota in all sections are the same
            course["Quota for Each Section"] = str(quota[0])
        else:
            cat = parseToDict(section, quota)
            course["Quota"] = ""
            for key, value in cat.items():
                course["Quota"] += parseListToStr(value, ", ") + ": " + str(key) + "\n"
            course["Quota for Each Section"] = course["Quota"][:-1] # remove the last "\n"

        course["Total Quota"] = sum(quota)
        course["Section"] = parseListToStr(section, "\n")

        return course, error is None, error
    except Exception as e:
        return course, False, e
