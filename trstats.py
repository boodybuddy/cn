import argparse
import matplotlib.pyplot as plt
import pdb
import json
import subprocess
import statistics
import re
import os
import subprocess
import time
from collections import OrderedDict


def traceroutes(args):
    results = []
    for i in range(args.num_runs):
        temp_result = subprocess.run(['traceroute', '-m', str(args.max_hops), args.target], capture_output=True, text=True)
        print("num " + str(i + 1) + " run traceroute result \n" + temp_result.stdout)
        # print(temp_result.stdout)
        parsed_result = parse_output(temp_result.stdout)
        parsed_result = json.dumps(parsed_result, indent=2, ensure_ascii=False)
        parsed_result = json.loads(parsed_result)
        # print(parsed_result)
        results.append(parsed_result)
        time.sleep(args.run_delay)
    # print(results)
    return results

def traceroute_init(args):
    results=traceroutes(args)
    # print(results)
    combined_data = combined_traceroute_output(results)
    # print(combined_data)
    json_convert(combined_data, args.output)
    graph_plot(combined_data, args.graph)


def parse_output(output):
    lines = output.split('\n')
    result = {}
    hop = 1
    for line in lines:
        line = re.split(r'\s+', line)
        if not line[0]:del line[0]
        try:
            hop = int(line[0])
            del line[0]
        except:
            pass
        if not len(line):continue
        if line[0]=='*':continue
        if hop not in result:
            result[hop] = {"hosts":[], "delay":[]}
        
        result[hop]["hosts"].append([line[0],line[1]])
        for i in range(2, len(line), 2):
            result[hop]["delay"].append(float(line[i]))

    res = []
    for i in result:
        res.append(OrderedDict([("hop",i), 
                    ("min",min(result[i]["delay"])), 
                    ("max",max(result[i]["delay"])), 
                    ("avg",round(statistics.mean(result[i]["delay"]), 3)), 
                    ("med",statistics.median(result[i]["delay"])), 
                    ("hosts",result[i]["hosts"])]))
    return res


def combined_traceroute_output(results):
    hop_data_dict = {}

    for hops in results:
        for measurement in hops:
            hop_number = measurement["hop"]
            if hop_number not in hop_data_dict:
                hop_data_dict[hop_number] = {"avg_values": [], "min_values": [], "max_values": [], "med_values": [], "hosts": []}
            hop_data_dict[hop_number]["avg_values"].append(measurement["avg"])
            hop_data_dict[hop_number]["min_values"].append(measurement["min"])
            hop_data_dict[hop_number]["max_values"].append(measurement["max"])
            hop_data_dict[hop_number]["med_values"].append(measurement["med"])
            hop_data_dict[hop_number]["hosts"].append(measurement["hosts"])

    combined_hops = []

    for hop_number, data in hop_data_dict.items():
        avg = statistics.mean(data["avg_values"])
        combined_hops.append({
            "hop": hop_number,
            "min": min(data["min_values"]),
            "max": max(data["max_values"]),
            "avg": round(avg, 3),
            "med": statistics.median(data["med_values"]),
            "hosts": data["hosts"][0]
        })

    return sorted(combined_hops, key=lambda x: x["hop"])

def json_convert(combined_hop_data, output):
    with open(output, 'w') as json_file:
        json.dump(combined_hop_data, json_file, indent=6)


def graph_plot(data, graph):
    hops = [entry['hop'] for entry in data]
    min_values = [entry['min'] for entry in data]
    max_values = [entry['max'] for entry in data]
    avg_values = [entry['avg'] for entry in data]
    med_values = [entry['med'] for entry in data]

    plt.scatter(hops, min_values, label='Min', color='blue')
    plt.scatter(hops, max_values, label='Max', color='red')
    plt.scatter(hops, avg_values, label='Avg', color='green')
    plt.scatter(hops, med_values, label='Med', color='purple')

    plt.xlabel('Hop')
    plt.ylabel('delays(ms)')
    plt.title('Latency Analysis')
    plt.legend()
    plt.xticks(range(1, max(hops) + 1))
    
    plt.savefig(graph, format='pdf')
    plt.show()

def run_from_dir(test_dir, results):
    for filename in os.listdir(test_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(test_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    traceroute_output = file.read()
                print(f"Traceroute run from {file_path}:\n{traceroute_output}")
                parsed_result = parse_output(traceroute_output)
                results.append(parsed_result)
            else:
                print("file doesn't exist")

def nonzero_check(value):
    i=int(value)
    if i <= 0:
        raise argparse.ArgumentTypeError("please input positive integers for hops/delays/runs")
    return i

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", dest="num_runs", type=nonzero_check, default=1, help="Number of times traceroute will run")
    parser.add_argument("-d", dest="run_delay", type=nonzero_check, default=0, help="Number of seconds to wait between two consecutive runs")
    parser.add_argument("-m", dest="max_hops", type=nonzero_check, default=30, help="Number of times traceroute will run")
    parser.add_argument("-o", dest="output", help="Path and name of output JSON file containing the stats")
    parser.add_argument("-g", dest="graph", help="Path and name of output PDF file containing stats graph")
    parser.add_argument("-t", dest="target", help="A target domain name or IP address (required if --test is absent)")
    parser.add_argument("--test", dest="test_dir", help="Directory containing num_runs text files, each of which contains the output of a traceroute run. If present, this will override all other options and traceroute will not be invoked. Stats will be computed over the traceroute output stored in the text files")
    args = parser.parse_args()
    if args.test_dir:
        results=[]
        run_from_dir(args.test_dir, results)
    traceroute_init(args)
