import argparse
import json
import subprocess
import os
import time
import statistics
import re
import matplotlib.pyplot as plt

def run_traceroute(args):
    traceroute_results = []
    if args.test_directory:
        run_traceroute_from_files(args.test_directory, traceroute_results)
    else:
        run_traceroutes_live(args, traceroute_results)
    combined_data = combine_hop_data(traceroute_results)
    save_combined_data_to_json(combined_data, args.output_file)
    create_latency_graph(combined_data, args.graph_file)

def run_traceroutes_live(args, traceroute_results):
    for run_index in range(args.num_runs):
        traceroute_command = ['traceroute', '-m', str(args.max_hops), args.target]
        traceroute_output = subprocess.run(traceroute_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
        print(f"Traceroute run {run_index + 1} output:\n{traceroute_output}")
        parsed_result = parse_traceroute_output(traceroute_output)
        traceroute_results.append(parsed_result)
        if run_index < args.num_runs - 1:
            time.sleep(args.run_delay)

def parse_traceroute_output(output):
    hops = []
    pattern = re.compile(r'\s*(\d+)\s+(.*?)\s+\((.*?)\)\s+(\d+\.\d+)\s+ms\s+(\d+\.\d+)\s+ms\s+(\d+\.\d+)\s+ms')

    lines = output.split('\n')
    for line in lines:
        match = pattern.match(line)
        if match:
            latencies = [float(match.group(4)), float(match.group(5)), float(match.group(6))]
            hop = {
                'hop': int(match.group(1)),
                'avg': round(sum(latencies) / len(latencies), 3),
                'min': min(latencies),
                'max': max(latencies),
                'med': statistics.median(latencies),
                'hosts': [[match.group(3), f'({match.group(2)})']]
            }
            hops.append(hop)

    return hops

def combine_hop_data(results):
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

def save_combined_data_to_json(combined_hop_data, output_file):
    with open(output_file, 'w') as json_file:
        json.dump(combined_hop_data, json_file, indent=4)

def create_latency_graph(traceroutes, graph_file):
    hop_data = {}
    for hop in traceroutes:
        hop_label = f'Hop {hop["hop"]}'
        latency_values = [hop[latency_type] for latency_type in ['avg', 'max', 'min', 'med']]
        hop_data[hop_label] = latency_values

    plt.boxplot(hop_data.values(), labels=hop_data.keys(), showmeans=True, meanprops={"marker": "o"})
    plt.title('Latency Distribution per Hop')
    plt.xlabel('Hops')
    plt.ylabel('Latency (ms)')
    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig(graph_file, format='pdf')
    plt.show()

def run_traceroute_from_files(test_dir, results):
    for filename in os.listdir(test_dir):
        if filename.endswith(".out"):
            file_path = os.path.join(test_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    traceroute_output = file.read()
                print(f"Traceroute run from {file_path}:\n{traceroute_output}")
                parsed_result = parse_traceroute_output(traceroute_output)
                results.append(parsed_result)
            else:
                print(f"File {file_path} not found.")

if __name__ == "__main__":
    def positive_integer(value):
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
        return ivalue

    parser = argparse.ArgumentParser()

    parser.add_argument("-n", dest="num_runs", type=positive_integer, default=1, help="Number of times traceroute will run")
    parser.add_argument("-d", dest="run_delay", type=positive_integer, default=0, help="Number of seconds to wait between two consecutive runs")
    parser.add_argument("-m", dest="max_hops", type=positive_integer, default=30, help="Number of times traceroute will run")
    parser.add_argument("-o", dest="output", help="Path and name of output JSON file containing the stats")
    parser.add_argument("-g", dest="graph", help="Path and name of output PDF file containing stats graph")
    parser.add_argument("-t", dest="target", help="A target domain name or IP address (required if --test is absent)")
    parser.add_argument("--test", dest="test_directory", help="Directory containing num_runs text files, each of which contains the output of a traceroute run. If present, this will override all other options and traceroute will not be invoked. Stats will be computed over the traceroute output stored in the text files")
    args = parser.parse_args()
    run_traceroute(args)
