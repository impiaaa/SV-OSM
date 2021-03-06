def filterTags(attrs):
    tags = {"crossing": "no",
            "traffic_signals": "ramp_meter",
            "traffic_signals:hov": "no"}
    if attrs["EXISTING"] == "0":
        tags["proposed:highway"] = "traffic_signals"
    elif attrs["OPERATIONA"] == "0":
        tags["disused:highway"] = "traffic_signals"
    elif attrs["CONSTRUCTI"] == "y":
        tags["construction:highway"] = "traffic_signals"
    else:
        tags["highway"] = "traffic_signals"
    if attrs["INSTALLED"]:
        tags["start_date"] = attrs["INSTALLED"][:10]
    if attrs["COMMENTS"]:
        tags["note"] = attrs["COMMENTS"]
    if attrs["DAYS_OPERA"]:
        tags["traffic_signals:operating_times"] = "-".join([day[:2] for day in attrs["DAYS_OPERA"].split("-")])
    if attrs["TIME_OF_AC"]:
        if tags["traffic_signals:operating_times"]:
            tags["traffic_signals:operating_times"] += " "
        else:
            tags["traffic_signals:operating_times"] = ""
        startS, endS = attrs["TIME_OF_AC"].split("-")
        if startS.endswith("PM"):
            start = int(startS[:-2].strip())+12
        elif startS.endswith("AM"):
            start = int(startS[:-2].strip())
        else:
            start = int(startS.strip())
        if endS.endswith("PM"):
            end = int(endS[:-2].strip())+12
            if not startS.endswith("AM") and not startS.endswith("PM"):
                start += 12
        elif endS.endswith("AM"):
            end = int(endS[:-2].strip())
        else:
            end = int(endS.strip())
        tags["traffic_signals:operating_times"] += "%02d:00-%02d:00"%(start, end)
    return tags

