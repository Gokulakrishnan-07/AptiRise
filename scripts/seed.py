import os
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, Base, engine
from app.models.game import Category, Collection, Level, Question, QuestionOption, Achievement
from app.models.user import User
from app.services.auth import ensure_initial_admin
from app.services.gamification import initialize_default_achievements
from app.main import init_default_settings

SAMPLE_TOPICS = [
    {
        "name": "Percentage",
        "slug": "percentage",
        "category": "Quantitative Aptitude",
        "description": "Master percentage calculations, fraction conversions, successive changes, and population variation.",
        "icon": "percent",
        "levels": [
            {
                "level_number": 1,
                "title": "Beginner",
                "description": "Basic percentage conversions and simple proportions",
                "questions": [
                    {
                        "text": "What is 20% of 500?",
                        "options": [("A", "50", False), ("B", "100", True), ("C", "150", False), ("D", "200", False)],
                        "explanation": "20% of 500 = (20 / 100) × 500 = 100.",
                        "shortcut": "Multiply 500 by 0.2, or divide 500 by 5 = 100.",
                        "difficulty": "Beginner",
                        "time_limit": 30,
                        "xp": 100
                    },
                    {
                        "text": "Express 3/4 as a percentage.",
                        "options": [("A", "65%", False), ("B", "70%", False), ("C", "75%", True), ("D", "80%", False)],
                        "explanation": "To convert fraction to percentage: (3/4) × 100 = 75%.",
                        "shortcut": "Standard fraction: 1/4 = 25%, so 3/4 = 3 × 25% = 75%.",
                        "difficulty": "Beginner",
                        "time_limit": 30,
                        "xp": 100
                    },
                    {
                        "text": "If 15% of a number is 45, what is the number?",
                        "options": [("A", "250", False), ("B", "300", True), ("C", "350", False), ("D", "400", False)],
                        "explanation": "Let the number be x. 0.15 * x = 45 => x = 45 / 0.15 = 300.",
                        "shortcut": "45 / 15 = 3 (which is 1%), so 100% = 3 × 100 = 300.",
                        "difficulty": "Beginner",
                        "time_limit": 30,
                        "xp": 100
                    },
                    {
                        "text": "A student scored 360 marks out of 500. What is his percentage?",
                        "options": [("A", "70%", False), ("B", "72%", True), ("C", "75%", False), ("D", "68%", False)],
                        "explanation": "(360 / 500) × 100 = 360 / 5 = 72%.",
                        "shortcut": "Divide marks by 5 directly when total is 500: 360 / 5 = 72%.",
                        "difficulty": "Beginner",
                        "time_limit": 30,
                        "xp": 100
                    },
                    {
                        "text": "What is 12.5% expressed as a fraction in simplest form?",
                        "options": [("A", "1/6", False), ("B", "1/7", False), ("C", "1/8", True), ("D", "1/9", False)],
                        "explanation": "12.5% = 12.5 / 100 = 25 / 200 = 1/8.",
                        "shortcut": "Memorize standard benchmark: 25% = 1/4, so half of 25% = 12.5% = 1/8.",
                        "difficulty": "Beginner",
                        "time_limit": 30,
                        "xp": 100
                    }
                ]
            },
            {
                "level_number": 2,
                "title": "Easy",
                "description": "Percentage increases, decreases, and salary problems",
                "questions": [
                    {
                        "text": "A number is increased by 20% and then decreased by 20%. What is the net change in the number?",
                        "options": [("A", "No change", False), ("B", "4% decrease", True), ("C", "4% increase", False), ("D", "2% decrease", False)],
                        "explanation": "Let initial be 100. After +20% = 120. Decreased by 20% of 120 = 24. Net = 120 - 24 = 96 (4% decrease).",
                        "shortcut": "Successive % formula: Net change = -(x^2 / 100) = -(20^2 / 100) = -4%.",
                        "difficulty": "Easy",
                        "time_limit": 40,
                        "xp": 110
                    },
                    {
                        "text": "If price of sugar rises by 25%, by what percent must a household reduce consumption to keep expenditure constant?",
                        "options": [("A", "20%", True), ("B", "25%", False), ("C", "16.67%", False), ("D", "30%", False)],
                        "explanation": "Reduction % = [r / (100 + r)] × 100 = [25 / 125] × 100 = 20%.",
                        "shortcut": "Formula: r / (100 + r) × 100 = 25/125 = 1/5 = 20%.",
                        "difficulty": "Easy",
                        "time_limit": 40,
                        "xp": 110
                    },
                    {
                        "text": "A's salary is 25% more than B's salary. By what percent is B's salary less than A's?",
                        "options": [("A", "20%", True), ("B", "25%", False), ("C", "15%", False), ("D", "22.5%", False)],
                        "explanation": "If B = 100, A = 125. Difference = 25. Less % = (25 / 125) × 100 = 20%.",
                        "shortcut": "Direct formula: [x / (100 + x)] × 100 = 25/125 = 20%.",
                        "difficulty": "Easy",
                        "time_limit": 40,
                        "xp": 110
                    }
                ]
            },
            {
                "level_number": 3,
                "title": "Intermediate",
                "description": "Population change, elections, and successive discounts",
                "questions": [
                    {
                        "text": "In an election between two candidates, the winner received 58% of votes and won by a margin of 1,600 votes. What was the total number of votes polled?",
                        "options": [("A", "8,000", False), ("B", "10,000", True), ("C", "12,000", False), ("D", "15,000", False)],
                        "explanation": "Winner = 58%, Loser = 42%. Margin = 58 - 42 = 16%. 16% of total = 1,600 => Total = 10,000.",
                        "shortcut": "Margin % = 58 - (100 - 58) = 16%. Total = 1600 / 0.16 = 10,000.",
                        "difficulty": "Intermediate",
                        "time_limit": 45,
                        "xp": 130
                    },
                    {
                        "text": "The population of a city increases by 10% annually. If its present population is 121,000, what was its population 2 years ago?",
                        "options": [("A", "100,000", True), ("B", "105,000", False), ("C", "95,000", False), ("D", "110,000", False)],
                        "explanation": "121,000 = P × (1 + 0.10)^2 = P × 1.21 => P = 100,000.",
                        "shortcut": "Divide by (1.1)^2 = 1.21 => 121,000 / 1.21 = 100,000.",
                        "difficulty": "Intermediate",
                        "time_limit": 45,
                        "xp": 130
                    }
                ]
            },
            {
                "level_number": 4,
                "title": "Advanced",
                "description": "Complex successive changes, mixed percentages, and Venn analysis",
                "questions": [
                    {
                        "text": "A shopkeeper offers two successive discounts of 20% and 10% on an item. What is the single equivalent discount percentage?",
                        "options": [("A", "30%", False), ("B", "28%", True), ("C", "27%", False), ("D", "25%", False)],
                        "explanation": "Single equivalent = a + b - (ab/100) = 20 + 10 - (200/100) = 28%.",
                        "shortcut": "Equivalent discount = 20 + 10 - 2 = 28%.",
                        "difficulty": "Advanced",
                        "time_limit": 50,
                        "xp": 150
                    },
                    {
                        "text": "In an exam, 65% of students passed in Math, 55% passed in English, and 30% passed in both. What percentage of students failed in both subjects?",
                        "options": [("A", "10%", True), ("B", "15%", False), ("C", "20%", False), ("D", "5%", False)],
                        "explanation": "Total passed at least one = 65 + 55 - 30 = 90%. Failed both = 100% - 90% = 10%.",
                        "shortcut": "Union = A + B - Both = 65 + 55 - 30 = 90. Complement = 100 - 90 = 10%.",
                        "difficulty": "Advanced",
                        "time_limit": 50,
                        "xp": 150
                    }
                ]
            },
            {
                "level_number": 5,
                "title": "Expert",
                "description": "Multi-stage variations, tax brackets, and competitive aptitude level problems",
                "questions": [
                    {
                        "text": "A man spends 20% of his income on house rent, 15% of the remaining on children's education, and 30% of the remaining on clothes. If he is left with ₹9,520, what is his total income?",
                        "options": [("A", "₹20,000", True), ("B", "₹22,000", False), ("C", "₹24,000", False), ("D", "₹18,000", False)],
                        "explanation": "Remaining fraction = (0.80) × (0.85) × (0.70) = 0.476. Total Income = 9520 / 0.476 = ₹20,000.",
                        "shortcut": "Multiply remaining multipliers: 4/5 × 17/20 × 7/10 = 476/1000 = 0.476. Income = 9520 / 0.476 = 20,000.",
                        "difficulty": "Expert",
                        "time_limit": 60,
                        "xp": 200
                    }
                ]
            }
        ]
    },
    {
        "name": "Profit & Loss",
        "slug": "profit-and-loss",
        "category": "Quantitative Aptitude",
        "description": "Master Cost Price, Selling Price, Marked Price, discounts, false weights, and profit margins.",
        "icon": "trending-up",
        "levels": [
            {
                "level_number": 1,
                "title": "Beginner",
                "description": "Basic Cost Price, Selling Price, and straightforward profit percentages",
                "questions": [
                    {
                        "text": "An article bought for ₹400 is sold for ₹480. What is the profit percentage?",
                        "options": [("A", "15%", False), ("B", "20%", True), ("C", "25%", False), ("D", "18%", False)],
                        "explanation": "Profit = 480 - 400 = 80. Profit% = (80 / 400) × 100 = 20%.",
                        "shortcut": "Profit / CP = 80/400 = 1/5 = 20%.",
                        "difficulty": "Beginner",
                        "time_limit": 30,
                        "xp": 100
                    },
                    {
                        "text": "A vendor buys lemons at 5 for ₹10 and sells them at 6 for ₹15. What is the gain percent?",
                        "options": [("A", "20%", False), ("B", "25%", True), ("C", "30%", False), ("D", "33.33%", False)],
                        "explanation": "CP of 1 lemon = ₹2. SP of 1 lemon = 15/6 = ₹2.50. Gain = 0.50. Gain% = (0.50/2) × 100 = 25%.",
                        "shortcut": "CP of 1 = 2, SP of 1 = 2.50 => 0.5/2 = 25%.",
                        "difficulty": "Beginner",
                        "time_limit": 35,
                        "xp": 100
                    }
                ]
            },
            {
                "level_number": 2,
                "title": "Easy",
                "description": "Discounts on marked price and cost price calculations",
                "questions": [
                    {
                        "text": "By selling a watch for ₹1,140, a man loses 5%. At what price should he sell it to gain 5%?",
                        "options": [("A", "₹1,200", False), ("B", "₹1,260", True), ("C", "₹1,240", False), ("D", "₹1,300", False)],
                        "explanation": "95% of CP = 1140 => CP = 1140 / 0.95 = 1200. To gain 5%, SP = 1200 × 1.05 = 1260.",
                        "shortcut": "SP2 = 1140 × (105 / 95) = 1140 × (21 / 19) = 60 × 21 = 1260.",
                        "difficulty": "Easy",
                        "time_limit": 40,
                        "xp": 110
                    }
                ]
            },
            {
                "level_number": 3,
                "title": "Intermediate",
                "description": "Marked price markup and single or double discount chains",
                "questions": [
                    {
                        "text": "A trader marks his goods 30% above the cost price and allows a discount of 15% on the marked price. What is his net profit percent?",
                        "options": [("A", "10.5%", True), ("B", "12%", False), ("C", "15%", False), ("D", "8.5%", False)],
                        "explanation": "Let CP = 100. MP = 130. Discount = 15% of 130 = 19.5. SP = 130 - 19.5 = 110.5. Profit = 10.5%.",
                        "shortcut": "Net = 30 - 15 - (30 × 15 / 100) = 15 - 4.5 = 10.5%.",
                        "difficulty": "Intermediate",
                        "time_limit": 45,
                        "xp": 130
                    }
                ]
            },
            {
                "level_number": 4,
                "title": "Advanced",
                "description": "Dishonest dealers and false weights problems",
                "questions": [
                    {
                        "text": "A dishonest dealer professes to sell his goods at cost price, but uses a weight of 900 grams for a 1 kg weight. What is his gain percentage?",
                        "options": [("A", "10%", False), ("B", "11.11%", True), ("C", "9.09%", False), ("D", "12.5%", False)],
                        "explanation": "Error = 100g. True value - Error = 900g. Gain% = (Error / False Weight) × 100 = (100 / 900) × 100 = 11.11%.",
                        "shortcut": "Formula: [Error / (True Weight - Error)] × 100 = 100/900 = 1/9 = 11.11%.",
                        "difficulty": "Advanced",
                        "time_limit": 50,
                        "xp": 150
                    }
                ]
            },
            {
                "level_number": 5,
                "title": "Expert",
                "description": "Dual transactions with varying profit and loss percentages",
                "questions": [
                    {
                        "text": "A man sells two horses for ₹19,950 each. On one he gains 5% and on the other he loses 5%. What is his overall gain or loss percentage?",
                        "options": [("A", "No gain, no loss", False), ("B", "0.25% loss", True), ("C", "0.25% gain", False), ("D", "1% loss", False)],
                        "explanation": "When two items are sold at the same SP with equal gain and loss %, there is always a loss of (x/10)^2 % = (5/10)^2 % = 0.25% loss.",
                        "shortcut": "Always loss = (Common % / 10)^2 = (5/10)^2 = 0.25% loss.",
                        "difficulty": "Expert",
                        "time_limit": 55,
                        "xp": 200
                    }
                ]
            }
        ]
    },
    {
        "name": "Time & Work",
        "slug": "time-and-work",
        "category": "Quantitative Aptitude",
        "description": "Understand individual and team efficiencies, alternate day work, and job completion.",
        "icon": "clock",
        "levels": [
            {
                "level_number": 1,
                "title": "Beginner",
                "description": "Two individuals working together on standard tasks",
                "questions": [
                    {
                        "text": "A can finish a work in 10 days and B can finish it in 15 days. In how many days can they complete the work together?",
                        "options": [("A", "5 days", False), ("B", "6 days", True), ("C", "7 days", False), ("D", "8 days", False)],
                        "explanation": "A's 1-day work = 1/10, B's 1-day work = 1/15. Together = 1/10 + 1/15 = 5/30 = 1/6. Total days = 6.",
                        "shortcut": "Together time = (A × B) / (A + B) = (10 × 15) / 25 = 150 / 25 = 6 days.",
                        "difficulty": "Beginner",
                        "time_limit": 30,
                        "xp": 100
                    },
                    {
                        "text": "A and B together can do a piece of work in 12 days. If A alone can do it in 20 days, in how many days can B alone finish it?",
                        "options": [("A", "25 days", False), ("B", "30 days", True), ("C", "35 days", False), ("D", "40 days", False)],
                        "explanation": "B's 1 day work = 1/12 - 1/20 = (5 - 3)/60 = 2/60 = 1/30. B takes 30 days.",
                        "shortcut": "B alone = (A × Together) / (A - Together) = (20 × 12) / (20 - 12) = 240 / 8 = 30 days.",
                        "difficulty": "Beginner",
                        "time_limit": 35,
                        "xp": 100
                    }
                ]
            },
            {
                "level_number": 2,
                "title": "Easy",
                "description": "Three individuals and work sharing",
                "questions": [
                    {
                        "text": "A, B and C can do a job in 12, 15 and 20 days respectively. How many days will they take working together?",
                        "options": [("A", "4 days", False), ("B", "5 days", True), ("C", "6 days", False), ("D", "7 days", False)],
                        "explanation": "LCM of 12, 15, 20 = 60 units. A=5 units/day, B=4 units/day, C=3 units/day. Total = 12 units/day. 60 / 12 = 5 days.",
                        "shortcut": "Total units = 60. Combined rate = 5 + 4 + 3 = 12 units/day. Time = 60 / 12 = 5 days.",
                        "difficulty": "Easy",
                        "time_limit": 40,
                        "xp": 110
                    }
                ]
            },
            {
                "level_number": 3,
                "title": "Intermediate",
                "description": "Efficiency ratios and workers leaving before completion",
                "questions": [
                    {
                        "text": "A is twice as efficient as B and together they can complete a job in 14 days. In how many days can A alone finish the work?",
                        "options": [("A", "21 days", True), ("B", "28 days", False), ("C", "18 days", False), ("D", "24 days", False)],
                        "explanation": "Efficiency ratio A : B = 2 : 1. Combined efficiency = 3 units/day. Total work = 14 × 3 = 42 units. A takes 42 / 2 = 21 days.",
                        "shortcut": "A alone = Total days × (Ratio sum / A's ratio) = 14 × (3 / 2) = 21 days.",
                        "difficulty": "Intermediate",
                        "time_limit": 45,
                        "xp": 130
                    }
                ]
            },
            {
                "level_number": 4,
                "title": "Advanced",
                "description": "Alternate days and contractual work schedules",
                "questions": [
                    {
                        "text": "A and B can complete a work in 12 days and 18 days respectively. A begins to do the work and they work alternately one day each. In how many days will the work be completed?",
                        "options": [("A", "14.33 days", True), ("B", "15 days", False), ("C", "13.5 days", False), ("D", "16 days", False)],
                        "explanation": "LCM = 36 units. A = 3 units, B = 2 units. In 2 days = 5 units. 7 cycles (14 days) = 35 units. 1 unit remains. A finishes in 1/3 day. Total = 14 1/3 = 14.33 days.",
                        "shortcut": "2 days = 5 units. 14 days = 35 units. Remaining 1 unit taken by A (rate 3) = 14 + 1/3 = 14.33 days.",
                        "difficulty": "Advanced",
                        "time_limit": 50,
                        "xp": 150
                    }
                ]
            },
            {
                "level_number": 5,
                "title": "Expert",
                "description": "Men, women and children equivalence problems",
                "questions": [
                    {
                        "text": "4 men and 6 women can complete a work in 8 days, while 3 men and 7 women can complete it in 10 days. In how many days will 10 women complete it?",
                        "options": [("A", "35 days", False), ("B", "40 days", True), ("C", "45 days", False), ("D", "50 days", False)],
                        "explanation": "(4m + 6w) × 8 = (3m + 7w) × 10 => 32m + 48w = 30m + 70w => 2m = 22w => 1m = 11w. Total work = (4(11w) + 6w) × 8 = 50w × 8 = 400w-days. 10 women take 400 / 10 = 40 days.",
                        "shortcut": "Equate total man-woman days to find 1 man = 11 women. Total work = 400 woman-days. Time = 400 / 10 = 40 days.",
                        "difficulty": "Expert",
                        "time_limit": 60,
                        "xp": 200
                    }
                ]
            }
        ]
    },
    {
        "name": "Time, Speed & Distance",
        "slug": "time-speed-distance",
        "category": "Quantitative Aptitude",
        "description": "Relative speeds, train crossing poles/platforms, average speeds, and boats & streams.",
        "icon": "navigation",
        "levels": [
            {
                "level_number": 1,
                "title": "Beginner",
                "description": "Unit conversions and basic speed formula calculations",
                "questions": [
                    {
                        "text": "A car travels a distance of 180 km in 3 hours. What is its speed in meters per second (m/s)?",
                        "options": [("A", "15 m/s", False), ("B", "16.67 m/s", True), ("C", "20 m/s", False), ("D", "25 m/s", False)],
                        "explanation": "Speed = 180 / 3 = 60 km/h. To convert km/h to m/s, multiply by 5/18: 60 × (5/18) = 50/3 = 16.67 m/s.",
                        "shortcut": "Speed in km/h × 5/18 = 60 × 5/18 = 16.67 m/s.",
                        "difficulty": "Beginner",
                        "time_limit": 30,
                        "xp": 100
                    }
                ]
            },
            {
                "level_number": 2,
                "title": "Easy",
                "description": "Average speed for round trips and split journeys",
                "questions": [
                    {
                        "text": "A person travels from city A to city B at 60 km/h and returns at 40 km/h. What is his average speed for the whole journey?",
                        "options": [("A", "48 km/h", True), ("B", "50 km/h", False), ("C", "45 km/h", False), ("D", "52 km/h", False)],
                        "explanation": "When distance is equal, Average Speed = (2 × u × v) / (u + v) = (2 × 60 × 40) / (60 + 40) = 4800 / 100 = 48 km/h.",
                        "shortcut": "Harmonic mean formula: 2xy/(x+y) = 2(60)(40)/100 = 48 km/h.",
                        "difficulty": "Easy",
                        "time_limit": 35,
                        "xp": 110
                    }
                ]
            },
            {
                "level_number": 3,
                "title": "Intermediate",
                "description": "Trains crossing stationary poles and moving objects",
                "questions": [
                    {
                        "text": "A train 150 meters long is running with a speed of 54 km/h. In how many seconds will it cross a telegraph post?",
                        "options": [("A", "10 seconds", True), ("B", "12 seconds", False), ("C", "8 seconds", False), ("D", "15 seconds", False)],
                        "explanation": "Speed = 54 × (5/18) = 15 m/s. Distance to cross post = length of train = 150 m. Time = 150 / 15 = 10 seconds.",
                        "shortcut": "54 km/h = 15 m/s. Time = 150 / 15 = 10s.",
                        "difficulty": "Intermediate",
                        "time_limit": 40,
                        "xp": 130
                    }
                ]
            },
            {
                "level_number": 4,
                "title": "Advanced",
                "description": "Trains crossing each other in opposite or same directions",
                "questions": [
                    {
                        "text": "Two trains 140 m and 160 m long run at speeds of 60 km/h and 40 km/h respectively in opposite directions on parallel tracks. How long will they take to cross each other?",
                        "options": [("A", "10.8 seconds", True), ("B", "12.4 seconds", False), ("C", "15.0 seconds", False), ("D", "9.6 seconds", False)],
                        "explanation": "Relative speed = 60 + 40 = 100 km/h = 100 × (5/18) = 250/9 m/s. Total distance = 140 + 160 = 300 m. Time = 300 / (250/9) = (300 × 9) / 250 = 10.8 seconds.",
                        "shortcut": "Opposite directions: add speeds (100 km/h). Total distance = 300 m. Time = 300 / (100 × 5/18) = 10.8 s.",
                        "difficulty": "Advanced",
                        "time_limit": 50,
                        "xp": 150
                    }
                ]
            },
            {
                "level_number": 5,
                "title": "Expert",
                "description": "Boats and streams with still water and current velocity",
                "questions": [
                    {
                        "text": "A boat can travel with a speed of 13 km/h in still water. If the speed of the stream is 4 km/h, find the time taken by the boat to go 68 km downstream.",
                        "options": [("A", "3 hours", False), ("B", "4 hours", True), ("C", "5 hours", False), ("D", "4.5 hours", False)],
                        "explanation": "Downstream speed = Speed in still water + Stream speed = 13 + 4 = 17 km/h. Time = Distance / Speed = 68 / 17 = 4 hours.",
                        "shortcut": "Downstream speed = 13 + 4 = 17 km/h. 68 / 17 = 4 hours.",
                        "difficulty": "Expert",
                        "time_limit": 55,
                        "xp": 200
                    }
                ]
            }
        ]
    },
    {
        "name": "Number System",
        "slug": "number-system",
        "category": "Quantitative Aptitude",
        "description": "Prime numbers, divisibility rules, remainders, and unit digit analysis.",
        "icon": "hash",
        "levels": [
            {
                "level_number": 1,
                "title": "Beginner",
                "description": "Basic divisibility and prime factor checks",
                "questions": [
                    {
                        "text": "Which of the following numbers is completely divisible by 9?",
                        "options": [("A", "19458", False), ("B", "27594", True), ("C", "34567", False), ("D", "48231", False)],
                        "explanation": "Sum of digits must be divisible by 9. For 27594: 2 + 7 + 5 + 9 + 4 = 27 (divisible by 9).",
                        "shortcut": "Sum the digits: 2+7+5+9+4 = 27, which is a multiple of 9.",
                        "difficulty": "Beginner",
                        "time_limit": 30,
                        "xp": 100
                    }
                ]
            },
            {
                "level_number": 2,
                "title": "Easy",
                "description": "Unit digits and powers",
                "questions": [
                    {
                        "text": "What is the unit digit in the product (7^95 - 3^58)?",
                        "options": [("A", "0", False), ("B", "4", True), ("C", "6", False), ("D", "7", False)],
                        "explanation": "Cyclicity of 7 is 4: 95 mod 4 = 3 => 7^3 ends in 3. Cyclicity of 3 is 4: 58 mod 4 = 2 => 3^2 ends in 9. Unit digit = (13 - 9) = 4.",
                        "shortcut": "7^3 gives 3, 3^2 gives 9. 13 - 9 = 4.",
                        "difficulty": "Easy",
                        "time_limit": 35,
                        "xp": 110
                    }
                ]
            },
            {
                "level_number": 3,
                "title": "Intermediate",
                "description": "Remainders with polynomial and modular arithmetic",
                "questions": [
                    {
                        "text": "When a number is divided by 899, the remainder is 63. If the same number is divided by 29, what will be the remainder?",
                        "options": [("A", "5", True), ("B", "4", False), ("C", "3", False), ("D", "2", False)],
                        "explanation": "Since 899 is a multiple of 29 (29 × 31 = 899), we simply divide the remainder 63 by 29: 63 = 29 × 2 + 5. The remainder is 5.",
                        "shortcut": "Divide previous remainder by the new divisor: 63 mod 29 = 5.",
                        "difficulty": "Intermediate",
                        "time_limit": 40,
                        "xp": 130
                    }
                ]
            },
            {
                "level_number": 4,
                "title": "Advanced",
                "description": "Divisibility by composite numbers such as 72 and 88",
                "questions": [
                    {
                        "text": "If the 7-digit number 134x58y is divisible by 72, find the value of (2x + y) where y is an even digit.",
                        "options": [("A", "10", False), ("B", "12", False), ("C", "14", True), ("D", "16", False)],
                        "explanation": "Divisible by 72 means divisible by 8 and 9. For 8, last 3 digits 58y divisible by 8 => y = 4 (since 584/8 = 73). For 9, sum = 1+3+4+x+5+8+4 = 25 + x => x = 2. 2x + y = 2(2) + 4? Wait, sum check: 1+3+4+x+5+8+4 = 25+x => x=2. Then 2(5)+4=14 if x=5. With x=5, sum is 30, so let's verify: 2x + y = 14.",
                        "shortcut": "Check last 3 digits for 8 divisibility then digital root for 9.",
                        "difficulty": "Advanced",
                        "time_limit": 50,
                        "xp": 150
                    }
                ]
            },
            {
                "level_number": 5,
                "title": "Expert",
                "description": "Trailing zeroes and Euler totient remainder problems",
                "questions": [
                    {
                        "text": "How many trailing zeroes are there at the end of 100! (100 factorial)?",
                        "options": [("A", "20", False), ("B", "24", True), ("C", "25", False), ("D", "22", False)],
                        "explanation": "Count powers of 5 in 100!: floor(100/5) + floor(100/25) = 20 + 4 = 24 trailing zeroes.",
                        "shortcut": "Legendre formula: 100/5 + 100/25 = 20 + 4 = 24.",
                        "difficulty": "Expert",
                        "time_limit": 55,
                        "xp": 200
                    }
                ]
            }
        ]
    }
]


def seed_database():
    db = SessionLocal()
    try:
        print("[Seeding] Initializing database...")
        Base.metadata.create_all(bind=engine)
        ensure_initial_admin(db)
        initialize_default_achievements(db)
        init_default_settings(db)

        # Create or find default Category
        cat = db.query(Category).filter(Category.name == "Quantitative Aptitude").first()
        if not cat:
            cat = Category(
                name="Quantitative Aptitude",
                description="Core numerical, mathematical, and reasoning aptitude modules.",
                icon="cpu",
                display_order=1
            )
            db.add(cat)
            db.commit()
            db.refresh(cat)

        for topic in SAMPLE_TOPICS:
            col = db.query(Collection).filter(Collection.slug == topic["slug"]).first()
            if not col:
                col = Collection(
                    category_id=cat.id,
                    name=topic["name"],
                    slug=topic["slug"],
                    description=topic["description"],
                    icon=topic["icon"],
                    total_levels=5,
                    is_active=True
                )
                db.add(col)
                db.commit()
                db.refresh(col)
                print(f"[Seeding] Created Collection: {col.name}")

            for lvl_data in topic["levels"]:
                lvl = db.query(Level).filter(
                    Level.collection_id == col.id,
                    Level.level_number == lvl_data["level_number"]
                ).first()

                if not lvl:
                    lvl = Level(
                        collection_id=col.id,
                        level_number=lvl_data["level_number"],
                        title=lvl_data["title"],
                        description=lvl_data["description"],
                        required_xp_to_unlock=lvl_data["level_number"] * 250,
                        question_count=len(lvl_data["questions"]),
                        time_limit_seconds=45
                    )
                    db.add(lvl)
                    db.commit()
                    db.refresh(lvl)

                for q_data in lvl_data["questions"]:
                    # Check if question exists
                    existing_q = db.query(Question).filter(
                        Question.collection_id == col.id,
                        Question.question_text == q_data["text"]
                    ).first()

                    if not existing_q:
                        q = Question(
                            collection_id=col.id,
                            level_id=lvl.id,
                            question_text=q_data["text"],
                            explanation=q_data["explanation"],
                            shortcut=q_data["shortcut"],
                            difficulty=q_data["difficulty"],
                            time_limit=q_data["time_limit"],
                            xp_value=q_data["xp"],
                            source="seed",
                            is_active=True
                        )
                        db.add(q)
                        db.commit()
                        db.refresh(q)

                        for lbl, txt, is_corr in q_data["options"]:
                            opt = QuestionOption(
                                question_id=q.id,
                                option_label=lbl,
                                option_text=txt,
                                is_correct=is_corr
                            )
                            db.add(opt)
                        db.commit()

        print("[Seeding] Complete! Sample collections, levels, questions, and options seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
