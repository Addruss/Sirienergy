#!/bin/bash

BASE_URL="https://sirienergy.uab.cat"
REQUESTS=10000
CONCURRENCY=100

mkdir -p results_uni_mvc

tests=(
  "POST $BASE_URL/weather jsons/data_weather.json"
  "POST $BASE_URL/PVgen jsons/data_PVgen.json"
  "POST $BASE_URL/get_surplus_day jsons/data_get_surplus.json" 
)

# Initialize CSV (only add header if file doesn't exist)
CSV_FILE="results_uni_mvc/benchmark_results.csv"
if [[ ! -f "$CSV_FILE" ]]; then
  echo "Requests,Concurrency,time weather,time PVgen,time get_surplus_day" > "$CSV_FILE"
fi

# Arrays to store results
declare -A times

for test in "${tests[@]}"; do
  read method url json <<< "$test"
  name=$(basename "$url")
  mkdir -p "results_uni_mvc/result_${name}"
done


for test in "${tests[@]}"; do
  read method url json <<< "$test"
  name=$(basename "$url")
  result_file="results_uni_mvc/result_${name}/result_n${REQUESTS}_c${CONCURRENCY}_${name}.txt"

  echo "🚀 Starting test: $method $url"

  if [[ "$method" == "POST" ]]; then
    ab -n "$REQUESTS" -c "$CONCURRENCY" \
      -p "$json" \
      -T application/json \
      "$url" > "$result_file"
  else
    ab -n "$REQUESTS" -c "$CONCURRENCY" \
      "$url" > "$result_file"
  fi

  # Extract "Time per request: X [ms] (mean)" value - first occurrence
  time_value=$(grep "Time per request:" "$result_file" | head -1 | awk '{print $4}')
  times[$name]=$time_value
  echo "  ✓ $name: ${time_value} ms"
done

# Append CSV row
echo "$REQUESTS,$CONCURRENCY,${times[weather]},${times[PVgen]},${times[get_surplus_day]}" >> "$CSV_FILE"

echo "🏁 All sequential tests completed"
echo "📊 Results appended to $CSV_FILE"
