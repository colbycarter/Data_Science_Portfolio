# import libraries
import sys
import timeit
import datetime
from random import randint
import os

# define classes
class Workout:
    """Define parent workout class to be inhereted by three main workout types"""
    
    def __init__(self, location, workout_type=None, routine=None, duration=30, distance=0, rounds=1, units=None):
        location_dict = {"O": "Outdoor", "G": "Gym", "H": "Home/Indoor", "I": "Home/Indoor"}
        self.location = location_dict[location]

    def record_time(self):
        """start and stop workout timer for endurance exercises"""
        input("\nWhen you're ready to begin timing your " + self.routine + ", press [Enter]:")
        start = timeit.default_timer()
        input("\nHit [Enter] upon ending your " + self.routine + "...")
        stop = timeit.default_timer()
        return (stop - start) / 60    #in minutes
    
    def speed(self, time):
        """calculate average speed in miles (or flights) per hour, where time must be in minutes"""
        if self.units in ("miles","flights"):
            self.speed = self.distance / (time / 60)
        elif self.units == "meters":
            return (self.distance / 1609.34) / (time / 3600)
        else:
            print("Speed calc error")
    
    def calories(self, cals_per, distance=1, rounds=1, duration=1, multiplier=1):
        """Calculate estimate of calories burned"""
        return (cals_per * distance * rounds * duration * multiplier)

    def summarize(self):
        """To print a readable summary of the workout depending on workout type"""
        for_print = "\n".join(["\n" + "*" * 60,
                               " "*15 + str(datetime.date.today()) + " - Workout by STEVEFIT",
                               "*" * 60,
                               self.location+" - "+self.workout_type+" - "+self.routine,
                               "Summary ["])
        return for_print


class Outdoor(Workout):
    """Define child class for outdoor exercise routines and key cardio metrics"""
    
    def __init__(self, location, routine, distance=0, rounds=1):
        super().__init__(location)
        self.workout_type = "Cardio"
        cardio_dict = {"R": "Running", "S": "Sprints", "B": "Bicycling", "P": "Pick-up Basketball"}
        self.routine = cardio_dict[routine]
        if routine in "RB":
            self.units = "miles"
        elif routine in "S":
            self.units = "meters"
    
    def endurance(self):
        """capture endurance exercises of running and biking"""
        self.duration = super().record_time()
        self.distance = input_float("\n[Enter] your completed distance in miles: ")
        super().speed(self.duration)    #in mph
        if self.routine == "Running":
            x = self.speed / 7
        elif self.routine == "Bicycling":
            x = self.speed / 10
        self.calories = super().calories(60, self.distance, multiplier = x)    #60 cals per standard mile
        return None
    
    def sprints(self):
        """capture the times of sprints and get average speeds for each using speed() from Workout class"""
        self.distance = input_float("\n[Enter] distance of your sprint in meters (e.g., 100): ")
        self.rounds = int(input_float("\n[Enter] number of rounds: "))
        print("\n[Enter] the time of each split in seconds (DISCLAIMER: don't run with your computer):\n")
        self.sprint_list = []
        self.split_list = []
        for i in range(1, self.rounds+1):
            time = input_float("Split #" + str(int(i)) + ": ")
            self.sprint_list.append(time)
            self.split_list.append(super().speed(time))    #in MPH
        self.calories = super().calories(.5, self.distance, self.rounds)    #cals per meter

    def balling(self):
        """time basketball and estimate calorie burn"""
        self.duration = super().record_time()
        self.calories = super().calories(4, duration=self.duration)   #4 cals per minute
    
    def summarize(self):
        """To print a readable summary of the workout depending on workout type"""
        for_print = super().summarize()
        if self.routine in ("Running", "Bicycling"):
            for_print += ("Distance - Time - Avg. Speed - Calories Burned]:\n")
            for_print += (" "*8 + "{:.2f}".format(self.distance)+" "+self.units+"\n")
            for_print += (" "*8 + "{:.0f}".format(self.duration)+" minutes\n")
            for_print += (" "*8 + "{:.1f}".format(self.speed)+" "+self.units+" per hour (avg.)\n")
            
        elif self.routine == "Sprints":
            for_print += ("Distance - Rounds - Times - Avg. Speed - Calories Burned]:\n")
            for_print += (" "*8 + "{:.0f}".format(self.distance)+" meters - "+"{:.0f}".format(self.rounds)+" rounds\n")
            for i in range(self.rounds):
                for_print += (" "*8 + "{:.2f}".format(self.sprint_list[i]) + "s, " + 
                              "{:.1f}".format(self.split_list[i]) + "mph (avg.)\n")
        elif self.routine == "Pick-up Basketball":
            for_print += ("Duration - Calories Burned]:\n")
            for_print += (" "*8 + "{:.1f}".format(self.duration)+" minutes\n")
        else:
            for_print += "PRINT ERROR"
        for_print += (" "*8 + "{:.0f}".format(self.calories)+" calories burned (est.)\n")
        return for_print


class Gym(Workout):
    """Define child class for gym exercise routines and weight and cardio metrics"""
    
    def __init__(self, location, workout_type, routine=None):
        super().__init__(location)
        workout_dict = {"W": "Weights","C": "Cardio"}
        self.workout_type = workout_dict[workout_type]
    
    def weight_routine(self):
        """Get weight routine attributes and track counts entered by user"""
        self.units = "pounds"
        weight_dict = {"C": "Chest/Triceps", "T": "Chest/Triceps", "B": "Back/Biceps", "L": "Legs & Shoulders", "S": "Legs & Shoulders"}
        prompt = "\nWhich muscle group would you like to work on:[C]hest/[T]riceps, [B]ack/Biceps, or [L]egs-and-[S]houlders? "
        routine = input_str(prompt, "CTBLS")
        self.routine = weight_dict[routine]
        
        chest_list = ["Bench press", "Incline bench",  "Dumbell flies", "(Weighted) Dips"]
        back_list = ["Pull-ups (Weighted)", "Deadlifts", "Barbell rows", "Barbell curls"]
        leg_sh_list = ["Squats", "Military press", "Leg extensions", "Barbell shrugs"]
        exercise_list = {"C": chest_list, "T": chest_list, "B": back_list, "L": leg_sh_list, "S": leg_sh_list}
        self.exercises = exercise_list[routine]
        
        prompt = "\nWhat lifting set style would you like to do: [3]x3, [5]x5, [D]escending (10-8-6-4), or [P]yramid (8-6-4-6-8)? "
        lift_style = input_str(prompt, "35DP")
        lift_dict = {"3": "3x3", "5": "5x5", "D": "Descending", "P": "Pyramid"}
        self.lift_style = lift_dict[lift_style]
        target_dict = {"3": [3,3,3], "5": [5,5,5,5,5], "D": [10,8,6,4], "P": [8,6,4,6,8]}
        self.target = target_dict[lift_style]
        self.actuals = []
        self.weights = []
        self.max_weight = []
        self.next_workout = []
        
        for x in self.exercises:
            weight = input_float("\n[Enter] your starting weight for " + x + ": ")
            increment =  max(((weight * .1) // 5) * 5, 2.5)    #increments of 5, or min 2.5 for lower weights
            weight_list = []
            reps_list = []
            max_weight = weight
            for i in range(len(self.target)):
                weight_list.append(weight)
                prompt = "Set #" + str(i+1) + " target: " + "{:.1f}".format(weight) + " lbs., " + str(self.target[i]) + " reps - [Enter] actual reps: "
                reps = input_float(prompt)
                reps_list.append(reps)
                max_weight = max(max_weight, one_rep_max(weight, reps))
                if i < len(self.target)-1:
                    if self.target[i] < self.target[i+1]:
                        weight -= increment
                    elif self.target[i] > self.target[i+1]:
                        weight += increment
            self.weights.append(weight_list)
            self.actuals.append(reps_list)
            self.max_weight.append(max_weight)
            if sum(reps_list) >= sum(self.target):
                self.next_workout.append("Target met--Go up 5 lbs.!")
            else:
                self.next_workout.append("Re-try at current weights")


    def cardio_routine(self):
        cardio_dict = {"T": "Treadmill", "B": "Bike", "E": "Eliptical", "S": "Stair-stepper", "H": "Heavybag"}
        prompt = "\nWhich cardio routine would you like to do: use [T]readmill, [B]ike, [E]liptical, [S]tair-stepper, or [H]eavybag?\n"
        routine = input_str(prompt, "TBESH")
        self.routine = cardio_dict[routine]
        if self.routine != "Heavybag":
            self.duration = input_float("\nFor how many minutes will you use the " + self.routine + "? ")
        if self.routine in ["Treadmill", "Bike", "Eliptical"]:
            input("\nHit [Enter] to begin...")
            self.units = "miles"
            self.distance = input_float("\n[Enter] your distance in miles once completed: ")
            super().speed(self.duration)    #in MPH
            if self.routine == "Treadmill":
                x = self.speed / 7
            elif self.routine == "Bike":
                x = self.speed / 12
            else:
                x = self.speed / 6
            self.calories = super().calories(60, self.distance, multiplier = x)
        elif self.routine == "Stair-stepper":
            input("\nHit [Enter] to begin...")
            self.units = "flights"
            self.distance = input_float("\n[Enter] the number of flights walked once completed: ")
            super().speed(self.duration)    #in flights per hour
            self.calories = super().calories(10, duration=self.duration)
        elif self.routine == "Heavybag":
            self.units = "strikes"
            self.duration = super().record_time()
            self.calories = super().calories(8, duration=self.duration)
        return None

    def summarize(self):
        """To print a readable summary of the workout depending on workout type"""
        for_print = super().summarize()
        if self.workout_type == "Weights":
            for_print += ("Exercise - Weight - Reps (Target) - 1RM - Result]:\n")
            for x in range(len(self.exercises)):
                for_print += (self.exercises[x] + ":\n")
                for i in range(len(self.target)):
                    for_print += (" "*8 + "{:.0f}".format(self.weights[x][i]) + " lbs - " + "{:.0f}".format(self.actuals[x][i]) + " (" + "{:.0f}".format(self.target[i]) + ")\n")
                for_print += (" "*8 + "1RM = " + "{:.1f}".format(self.max_weight[x]) + "\n")
                for_print += (" "*8 + "Next workout: "+ self.next_workout[x]+"\n\n")
        elif self.routine in ["Treadmill", "Bike", "Eliptical", "Stair-stepper"]:
            for_print += ("Distance - Time - Avg. Speed - Calories Burned]:\n")
            for_print += (" "*8 + "{:.2f}".format(self.distance)+" "+self.units+"\n")
            for_print += (" "*8 + "{:.0f}".format(self.duration) + " minutes\n")
            for_print += (" "*8 + "{:.1f}".format(self.speed)+" "+self.units+" per hour (avg.)\n")
            for_print += (" "*8 + "{:.0f}".format(self.calories)+ " calories burned (est.)\n\n")
        elif self.routine == "Heavybag":
            for_print += ("Time - Calories Burned]:\n")
            for_print += (" "*8 + "{:.2f}".format(self.duration) + " mins - " + "{:.0f}".format(self.calories)+ " calories burned (est.)\n\n")
        else:
            for_print = "PRINT ERROR"
        return for_print


class Home(Workout):
    """Define child class for home high-intensity routine with exercises and supersets"""
    
    def __init__(self, location, routine, rounds=1, repetitions=10):
        super().__init__(location)
        exercises = ["Push-ups", "Pull-ups", "Speed squats", "Lunges (alternating)", "DB shoulder press", 
                     "DB shrugs", "DB curls", "Kettlebell swings", "DB T's", "Diamond push-ups", "Sit-ups"]
        self.workout_type = "High-Intensity"
        self.rounds = rounds
        self.repetitions = repetitions
        self.exercises = []
        if routine == "S":
            self.routine = "Selected"
            print("\nEnter [Y] if you would like to include the proposed exercise in your HIT superset, [N] to reject it:\n")
            for i in range(len(exercises)):
                x = input(exercises[i]+"? ").upper()
                if x == "Y":
                    self.exercises.append(exercises[i])
        elif routine == "R":
            self.routine = "Random"
            exercise_count = 0
            while exercise_count < 1 or exercise_count > len(exercises):
                prompt = "\n[Enter] the number of excercises you would like in a round (up to "+"{:.0f}".format(len(exercises))+"): "
                exercise_count = int(input_float(prompt))
            for i in range(exercise_count):
                self.exercises.append(exercises.pop(randint(0,len(exercises)-1)))
        else:
            print("ERROR selecting home workout")
        return None

    def start_HIT(self):
        print("\nHit [Enter] when you're ready to begin and again each time you've completed the assigned exercise")
        quit_program(input("(no breaks unless otherwise stated)...\n"))
        for i in range(1, self.rounds+1):
            print("Round #" + "{:.0f}".format(i) + ":")
            for x in self.exercises:
                quit_program(input(x + " - " + "{:.0f}".format(self.repetitions) + " reps"))
            if i < self.rounds:
                quit_program(input("\nTake a " + "{:.0f}".format(30*i) + " second break, then hit [Enter]... "))
        self.calories = self.rounds * self.repetitions * len(self.exercises) * 1.5   # 1.5 cal per rep
        return None
    
    def summarize(self):
        """To print a readable summary of the workout depending on workout type"""
        for_print = super().summarize()
        for_print += ("Exercise - Rounds x Repetitions - Calories Burned]:\n")
        for x in self.exercises:
            for_print += (" "*8 + x + " "*(20-len(x)) + "{:.0f}".format(self.rounds) + "x" + "{:.0f}".format(self.repetitions) + "\n")
        for_print += (" "*8 + "{:.0f}".format(self.calories)+ " calories burned (est.)\n\n")
        return for_print


# def key functions
def print_header():
    """print header to the workout application giving instructions"""
    print("\n" + "*" * 60 + "STEVEFIT" + "*" * 60)
    print(" " * 16 + "Welcome to Colby's archaic-looking alternative to the famous workout application JEFIT,")
    print(" " * 20 + "...built for when you're exercising with your computer's command line handy.\n")
    print("(If for some regrettable reason you must quit the workout prematurely, enter [Q] following any prompt and prepare to be shamed.)")
    input("\nHit [Enter] to begin...")
    print("*" * 60 + "STEVEFIT" + "*" * 60 + "\n")
    return None

def one_rep_max(max_weight, max_reps):
    """estimate maximum weight one repetition"""
    max_dict = {1: 1.0, 2: .95, 3: .925, 4: .9, 5: .875, 6: .85, 7: .825, 8: .8, 9: .775}
    if max_reps < 10:
        return max_weight / max_dict[max_reps]
    else:
        return max_weight / .75
        
def quit_program(entry):
    """Function to let user end workout"""
    if entry.upper() == "Q":
        confirm = input("Are you really quitting already (Y/N)? ")
        if confirm.upper() == "Y":
            print("Shame! Pick it up again tomorrow. Goodbye.")
            sys.exit()
    return None

def input_str(prompt, acceptables):
    """Error handle for invalid string responses"""
    response = input(prompt).upper()
    quit_program(response)
    while response not in acceptables or response == "":
        response = input("Not a valid option. Try again: ").upper()
        quit_program(response)
    return response

def input_float(prompt):
    """Error handle for invalid numerical entries"""
    response = 0
    while True:
        try:
            response = input(prompt)
            quit_program(response)
            response = float(response)
            if response <= 0:
                raise Exception("Not a valid number. Try again.")
        except ValueError:
            print("Not a valid number. Try again.")
        except Exception as e:
            print(e)
        else:
            break
    return response

# main program
os.system('cls')
print_header()

prompt = "\nPlease type the letter corresponding to your desired workout location then hit [Enter]: [O]utdoor, [G]ym, or [H]ome/[I]ndoor:\n"
location = input_str(prompt, "OGHI")

if location.upper() == "O":
    prompt = "\nWhich routine would you like? Enter [R]unning, [S]prints, [B]icycling, or [P]ick-up Basketball:\n"
    routine = input_str(prompt, "RSBP")
    workout = Outdoor(location, routine)
    if routine in "RB":
        workout.endurance()
    elif routine == "S":
        workout.sprints()
    elif routine == "P":
        workout.balling()
elif location.upper() == "G":
    prompt = "\nAt the gym, will you lift [W]eights or do [C]ardio? "
    workout_type = input_str(prompt, "WC")
    workout = Gym(location, workout_type)
    if workout_type == "W":
        workout.weight_routine()
    elif workout_type == "C":
        workout.cardio_routine()
elif location.upper() in "HI":
    prompt = "\nWould you like to [S]elect your home HIT (high-intensity training) exercises or get a [R]andom selection?\n"
    routine = input_str(prompt,"SR")
    prompt = "\nHow many supersets, i.e. rounds, would you like to do? "
    rounds = int(input_float(prompt))
    prompt = "\nAnd how many repetitions of each exercise would you like to do? "
    reps = int(input_float(prompt))
    workout = Home(location, routine, rounds, reps)
    workout.start_HIT()

print("\n" + workout.summarize())
# print to external text file
workout_log = open("Workout_Log.txt","a")
workout_log.write(workout.summarize())
workout_log.close()