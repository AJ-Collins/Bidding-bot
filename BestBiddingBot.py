import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoAlertPresentException, WebDriverException, ElementClickInterceptedException
import time
from tkinter import Tk, Label, Button, Text, Entry, END

class Logger:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.insert(END, message + '\n')
        self.text_widget.see(END)  # Scroll to the end

    def flush(self):
        pass

class StudyPoolBidding:
    all_tasks = set()  # Store all collected tasks IDs across all sessions

    def __init__(self, email, password, logger):
        self.email = email
        self.password = password
        self.logger = logger
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 20)
        self.child_id = None
        self.available_tasks = set()  # Store available tasks IDs for each session
        self.bidded_tasks = set()  # Store bidded tasks IDs for each session

    def login(self):
        try:
            self.driver.get("https://www.studypool.com/")
            time.sleep(4)
            self.driver.find_element(By.LINK_TEXT, "Login").click()
            self.logger.write("Logging in...")
            time.sleep(3)
            self.driver.find_element(By.ID, "UserLogin_username").send_keys(self.email)
            time.sleep(3)
            self.driver.find_element(By.ID, "UserLogin_password").send_keys(self.password)
            time.sleep(3)
            self.driver.find_element(By.ID, "login-button").click()
            self.logger.write("Login successful!")
            time.sleep(3)  # Wait for potential captcha
            if "captcha" in self.driver.page_source.lower():
                self.logger.write("Captcha detected. Please solve the captcha manually.")
                while "captcha" in self.driver.page_source.lower():
                    time.sleep(100)  # Wait for the user to solve the captcha
            return True
        except Exception as e:
            self.logger.write(f"Login error: {e}")
            return False

    def go_to_boost_earnings_tab(self):
        try:
            time.sleep(3)
            self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "boost-earnings-tab"))).click()
            self.logger.write("Navigating to boost earnings tab. Please wait...")
            return True
        except TimeoutException as e:
            self.logger.write(f"Timeout error while navigating to boost earnings tab: {e}")
            return False
        except NoSuchElementException as e:
            self.logger.write(f"Element not found error while navigating to boost earnings tab: {e}")
            return False

    def bid_on_tasks(self):
        consecutive_failures = 0
        while True:
            try:
                # Find all available tasks
                task_elements = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "question-list-entry")))
                self.available_tasks = set()  # Reset available tasks set for this session
                for task_element in task_elements:
                    try:
                        child_element = task_element.find_element(By.XPATH, ".//*[starts-with(@id, 'left-')]")
                        self.child_id = child_element.get_attribute("id")  # Extract ID
                        if self.child_id in self.bidded_tasks:
                            self.logger.write(f"Task {self.child_id} already bidded. Skipping...")
                            continue
                        if self.child_id in self.all_tasks:
                            self.logger.write(f"Task {self.child_id} already collected in previous session. Skipping...")
                            continue
                        if self.child_id in self.available_tasks:
                            self.logger.write(f"Task {self.child_id} already collected. Skipping...")
                            continue
                        self.available_tasks.add(self.child_id)  # Add task to available tasks set
                        task_element.click()

                        # Try to switch to the new window
                        if self.switch_to_new_window():
                            # If successfully switched, submit the bid
                            self.submit_bid()
                            consecutive_failures = 0  # Reset the counter on success
                        else:
                            # If no new window opened, increment the failure counter
                            consecutive_failures += 1
                            if consecutive_failures >= 5:
                                self.logger.write("Refreshing the page after 5 consecutive failures...")
                                self.driver.refresh()
                                time.sleep(5)
                                consecutive_failures = 0  # Reset the counter after refresh
                            break

                        # Add task ID to bidded tasks set
                        self.bidded_tasks.add(self.child_id)
                        # Add task ID to all tasks set
                        self.all_tasks.add(self.child_id)
                    except ElementClickInterceptedException:
                        self.logger.write("Element click intercepted. Skipping task...")
                        continue
                    except TimeoutException as e:
                        self.logger.write(f"Timeout error: {e}")
                        continue
                    except NoSuchElementException as e:
                        self.logger.write(f"Element not found error: {e}")
                        continue
            except Exception as e:
                self.logger.write(f"An error occurred: {e}")
                continue
            time.sleep(15)  # Keep the script running indefinitely, adjust sleep time as needed

    def switch_to_new_window(self):
        self.logger.write(f"Switching to new bidding tab...")
        try:
            WebDriverWait(self.driver, 5).until(EC.number_of_windows_to_be(2))
            self.driver.switch_to.window(self.driver.window_handles[1])
            return True
        except TimeoutException:
            self.logger.write(f"No new window to open")
            return False
        except NoSuchElementException:
            self.logger.write(f"Window not able to open")
            return False

    def submit_bid(self):
        try:
            time.sleep(3)
            self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "label-checkbox"))).click()
            time.sleep(3)
            try:
                # Handling captcha if present
                alert = self.driver.switch_to.alert
                alert.dismiss()
                self.logger.write("Captcha alert handled.")
            except NoAlertPresentException:
                pass

            time.sleep(3)
            self.wait.until(EC.element_to_be_clickable((By.ID, "placeABidButton"))).click()
            popup_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-popupid='42']"))
            )
            time.sleep(3)
            self.logger.write("Submitting bid...")
            popup_element.click()
            self.close_current_tab()
        finally:
            self.close_current_tab()

    def close_current_tab(self):
        try:
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                self.logger.write("Returning to main tab...")
            else:
                self.logger.write("No more windows to switch to.")
        except WebDriverException as e:
            if "invalid session id" in str(e).lower():
                self.logger.write("Invalid session ID error. Continuing...")
                return
            else:
                self.logger.write(f"An error occurred while closing the tab: {e}")
        except Exception as e:
            self.logger.write(f"An error occurred while closing the tab: {e}")
        time.sleep(2)

class StudyPoolGUI:
    def __init__(self, root):
        self.root = root
        root.title("StudyPool Bidding")

        self.label_email = Label(root, text="Email:")
        self.label_email.pack()
        self.entry_email = Entry(root)
        self.entry_email.pack()

        self.label_password = Label(root, text="Password:")
        self.label_password.pack()
        self.entry_password = Entry(root, show="*")
        self.entry_password.pack()

        self.start_button = Button(root, text="Start Bidding", command=self.start_bidding)
        self.start_button.pack()

        self.log_text = Text(root, height=10, width=50)
        self.log_text.pack()

        # Create a logger instance
        self.logger = Logger(self.log_text)

    def start_bidding(self):
        email_data = self.entry_email.get()
        password_data = self.entry_password.get()

        bidding_bot = StudyPoolBidding(email_data, password_data, self.logger)

        def run_bidding():
            if bidding_bot.login():
                if bidding_bot.go_to_boost_earnings_tab():
                    self.logger.write("Successfully navigated to boost earnings tab.")
                    # Stay on the boost earnings tab without doing anything else
                    bidding_bot.bid_on_tasks()
                else:
                    self.logger.write("Failed to navigate to boost earnings tab.")

        # Run the bidding bot in a separate thread to keep the GUI responsive
        threading.Thread(target=run_bidding).start()

if __name__ == "__main__":
    root = Tk()
    app = StudyPoolGUI(root)
    root.mainloop()
