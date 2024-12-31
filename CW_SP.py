import random
from collections import deque



NUM_TRACKS = 10000
SECTORS_PER_TRACK = 500
SEEK_TIME_PER_TRACK = 0.5
FULL_SEEK_TIME = 10
RPM = 7500
ROTATIONAL_DELAY = ((60 * 1000) / RPM) / 2
READ_WRITE_TIME_PER_SECTOR = ROTATIONAL_DELAY / SECTORS_PER_TRACK

NUM_BUFFERS = 10
READ_SYSTEM_CALL_TIME = 0.15
WRITE_SYSTEM_CALL_TIME = 0.15
INTERRUPT_HANDLING_TIME = 0.05
TIME_QUANTUM = 20
PROCESSING_TIME = 7  # ms

class Disk:
    def __init__(self):
        self.current_track = 0
        self.direction = "right"

    def calculate_seek_time(self, target_track):
        if target_track == self.current_track:
            return 0
        return abs(target_track - self.current_track) * SEEK_TIME_PER_TRACK

    def move_to_track(self, target_track):
        seek_time = self.calculate_seek_time(target_track)
        self.current_track = target_track
        return seek_time

class BufferCache:
    def __init__(self):
        self.hot_cache = deque(maxlen=NUM_BUFFERS // 2)
        self.cold_cache = deque(maxlen=NUM_BUFFERS // 2)
        self.modified = set()

    def access(self, sector, is_write=False):
        if sector in self.hot_cache:
            print(f"Accessing sector {sector} in hot cache. (Hit)")
            self.hot_cache.remove(sector)
            self.hot_cache.append(sector)
        elif sector in self.cold_cache:
            print(f"Promoting sector {sector} from cold cache to hot cache. (Miss)")
            self.cold_cache.remove(sector)
            if len(self.hot_cache) >= NUM_BUFFERS // 2:
                evicted = self.hot_cache.popleft()
                print(f"Evicting sector {evicted} from hot cache.")
                if evicted in self.modified:
                    print(f"Writing modified sector {evicted} to disk.")
                    self.modified.remove(evicted)
            self.hot_cache.append(sector)
        else:
            print(f"Loading sector {sector} into cold cache.")
            if len(self.cold_cache) >= NUM_BUFFERS // 2:
                evicted = self.cold_cache.popleft()
                print(f"Evicting sector {evicted} from cold cache.")
                if evicted in self.modified:
                    print(f"Writing modified sector {evicted} to disk.")
                    self.modified.remove(evicted)
            self.cold_cache.append(sector)

        if is_write:
            self.modified.add(sector)

    def get_cache_state(self):
        return {
            "hot": list(self.hot_cache),
            "cold": list(self.cold_cache)
        }

class Scheduler:
    def __init__(self, algorithm):
        self.algorithm = algorithm
        self.requests = []

    def add_request(self, request):
        self.requests.append(request)

    def schedule_LOOK(self, current_track, direction):
        seek_sequence = []
        left = [req for req in self.requests if req < current_track]
        right = [req for req in self.requests if req > current_track]

        left.sort()
        right.sort()

        run = 2
        seek_count = 0

        while run:
            if direction == "left":
                for track in reversed(left):
                    seek_sequence.append(track)
                    seek_count += abs(current_track - track)
                    current_track = track
                direction = "right"
            elif direction == "right":
                for track in right:
                    seek_sequence.append(track)
                    seek_count += abs(current_track - track)
                    current_track = track
                direction = "left"
            run -= 1

        self.requests = []
        return seek_sequence, seek_count

    def schedule_FLOOK(self, current_track):
        inward = [req for req in self.requests if req >= current_track]
        outward = [req for req in self.requests if req < current_track]
        inward.sort()
        outward.sort()

        if inward:
            next_request = inward.pop(0)
        elif outward:
            next_request = outward.pop(0)
        else:
            return None

        self.requests = inward + outward
        return next_request

    def schedule(self, current_track):
        if self.algorithm == "FIFO":
            return self.requests.pop(0)
        elif self.algorithm == "LOOK":
            return self.schedule_LOOK(current_track, "right")
        elif self.algorithm == "FLOOK":
            return self.schedule_FLOOK(current_track)
        else:
            raise ValueError("Unknown scheduling algorithm")

class Process:
    def __init__(self, pid, requests):
        self.pid = pid
        self.requests = requests
        self.processing_time = PROCESSING_TIME

    def process_request(self):
        if self.requests:
            return self.requests.pop(0)
        return None

def display_startup_info():
    print("Starting...")
    print("Algorithms Used:")
    print("- Buffer Cache: Two-Segment LRU (Hot and Cold)")
    print("- Scheduling: FIFO, LOOK, FLOOK")
    print("================================================\n")
    print(f"Settings: NUM_TRACKS: {NUM_TRACKS}\n RPM: {RPM} \n NUM_BUFFERS: {NUM_BUFFERS} \n Processing time: {PROCESSING_TIME}")

def simulate(num_processes, scheduler_algorithm):
    display_startup_info()

    disk = Disk()
    buffer_cache = BufferCache()
    scheduler = Scheduler(scheduler_algorithm)

    # Process queues
    run_queue = deque()
    sleep_queue = deque()

    processes = [
        Process(pid, [random.randint(0, NUM_TRACKS - 1) for _ in range(random.randint(5, 15))])
        for pid in range(num_processes)
    ]

    for process in processes:
        run_queue.append(process)

    time_elapsed = 0
    while run_queue or sleep_queue:
        while sleep_queue:
            run_queue.append(sleep_queue.popleft())

        if not run_queue:
            break

        current_process = run_queue.popleft()

        if current_process.requests:
            request = current_process.process_request()
            scheduler.add_request(request)
            print(f"Process {current_process.pid} added request for track {request}.")

        while scheduler.requests:
            if scheduler.algorithm == "LOOK":
                seek_sequence, seek_count = scheduler.schedule_LOOK(disk.current_track, disk.direction)
                for next_request in seek_sequence:
                    seek_time = disk.move_to_track(next_request)
                    buffer_cache.access(next_request, is_write=random.choice([True, False]))

                    time_elapsed += seek_time
                    time_elapsed += ROTATIONAL_DELAY
                    time_elapsed += READ_WRITE_TIME_PER_SECTOR

                    print(f"Processed request for track {next_request}. Time elapsed: {time_elapsed:.2f} ms")
                print(f"LOOK Seek Sequence: {seek_sequence}. Total seek count: {seek_count}")
            else:
                next_request = scheduler.schedule(disk.current_track)
                if next_request is None:
                    break

                seek_time = disk.move_to_track(next_request)
                buffer_cache.access(next_request, is_write=random.choice([True, False]))

                time_elapsed += seek_time
                time_elapsed += ROTATIONAL_DELAY
                time_elapsed += READ_WRITE_TIME_PER_SECTOR

                print(f"Processed request for track {next_request}. Time elapsed: {time_elapsed:.2f} ms")

        # Simulate process work after handling requests
        time_elapsed += current_process.processing_time
        print(f"Process {current_process.pid} processed data for {current_process.processing_time} ms.")

        if current_process.requests:
            sleep_queue.append(current_process)

    print(f"Simulation completed. Total time: {time_elapsed:.2f} ms")

# 2 processes
simulate(num_processes=2, scheduler_algorithm="LOOK")
