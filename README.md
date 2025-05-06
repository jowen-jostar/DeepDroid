# DeepDroid

---

## About

This repository contains the code for the system for the paper: **DeepDroid: Android GUI Testing with Multi-Context LLM Guidance**.

For accessing the datasets, you could download them from [*FestiVAL*](https://github.com/PKU-ASE-RISE/FestiVal) and [*FrUITeR*](https://felicitia.github.io/FrUITeR/).

---

## How to install

Make sure you have:
1. `Python`
2. `UIAutomator2`
3. `Android SDK`
4. Added directory in Android SDK to `platform_tools` `PATH`

Then clone this repo and install with: 
`git clone https://github.com/MobileLLM/AutoDroid.git`

---

## How to use

1. Prepare:

    - If you want to test the apps tested in our paper, please download them from the dataset above, and prepare an actual device or an emulator connected to your host machine via `adb`.
    - If you want to test other apps, please download the apk file, and prepare an actual device or an emulator connected to your host machine via `adb`.
    - Prepare a DeepSeek API key, or you can prepare a ChatGPT API key and change the code for LLM interaction in `DeepDroid/LLM.py` if desired.

2. Start:
   
   1. Modify the configurations in `DeepDroid/PreExplore/DataBasePE.py` and `DeepDroid/DataBase.py` according to your situation, including `AVD_SERIAL`, `api_key`, etc.
   2. Prepare the test file `DeepDroid/PreExplore/app_info.csv` for **PreExplore**, you can use the `app_info_festival.csv` and `app_info_fruiter.csv` we provide. 
   3. Run `DeepDroid/PreExplore/run_this.py`, and after **PreExplore**, it will generate `functions.json` and `states.json` files for subsequent stages.
   4. Prepare the test file `DeepDroid/test_info.csv` for **DeepDroid**, you can use the `test_info_festival.csv` and `test_info_fruiter.csv` we provide. 
   5. Run `DeepDroid/run_this.py`, and after testing is complete, it will generate `test_record` files containing test records and evaluation metrics used in our paper.

---

## Limitations

- The current implementation may make it difficult for LLM to determine whether a task has finished, resulting in difficulty in self stopping.
- Due to the randomness of LLM, the diversity of application GUI, and the subjectivity of task description in test cases, the performance of GUI testing may be unstable.

---

## Team

Hidden due to paper submission.