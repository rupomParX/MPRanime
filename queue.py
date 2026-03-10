#..........This Bot Made By [RAHAT](https://t.me/r4h4t_69)..........#
#..........Anyone Can Modify This As He Likes..........#
#..........Just one requests do not remove my credit..........#
from collections import deque
from threading import Lock


user_queues = {} 
download_lock = Lock()  # To ensure thread-safe operations
global_queue = deque()  # Queue for all active downloads

def add_to_queue(user_id, username, link):
    with download_lock:
        # Add to the global queue as a tuple (username, link)
        global_queue.append((username, link))        
        # Add to the user's specific queue
        if user_id not in user_queues:
            user_queues[user_id] = deque()
        user_queues[user_id].append(link)

def remove_from_queue(user_id, link):
    with download_lock:
        # Remove from the global queue
        for task in list(global_queue):
            if task[1] == link:
                global_queue.remove(task)
                break
        
        # Remove from the user's specific queue
        if user_id in user_queues and link in user_queues[user_id]:
            user_queues[user_id].remove(link)
        
        # If no tasks remain for the user, remove the user from `user_queues`
        if user_id in user_queues and not user_queues[user_id]:
            del user_queues[user_id]
            


