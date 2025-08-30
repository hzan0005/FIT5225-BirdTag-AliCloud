# BirdTag Project Comprehensive Testing Guide

This guide is designed to ensure all components of the BirdTag project, including the backend serverless services and the frontend user interface, are working as expected.

## Part 1: Backend API Script Testing

This section uses a Python script to directly interact with the APIs deployed on Alibaba Cloud, verifying the correctness of all backend logic.

### 1.1 Environment Preparation

1.  **Install Python**: Ensure Python 3.8 or a later version is installed on your computer.
2.  **Install `requests` Library**: `requests` is a Python library for making HTTP requests. Run the following command in your command line/terminal to install it:
    ```bash
    pip install requests
    ```
3.  **Prepare the Test Script**:
    * Name your final demonstration script `test_final.py`.
    * Ensure the script is the final version that includes authentication and can call all API endpoints.

### 1.2 Configure the Test Script

Open the `test_final.py` file and carefully check and modify the configuration section at the top:

* **`API_GATEWAY_DOMAIN`**: Confirm that this is your **final, working** API Gateway public domain name.
* **`USER_EMAIL` / `USER_PASSWORD`**: Set up a pair of user credentials for testing registration and login.
* **`FILE_URL_TO_MODIFY`**: Fill in an **original file URL** of an existing object in your database to test the "Manual Tag Management" feature.
* **`FILE_URL_TO_DELETE`**: **(Very Important)** Fill in a file URL that is **specifically for deletion testing**. It is recommended to first upload a "sacrificial" image and use its URL for the deletion test to avoid accidentally deleting important data.
* **`IMAGE_FILE_PATH`**: Fill in the **absolute path** of a real bird image file on your local computer to test the "Search by File" feature.

### 1.3 Execute the Tests

In your command line/terminal, navigate to the directory where the `test_final.py` script is located, and then run the following commands:

1.  **Test the Standard Flow (Register, Login, Query, Manage)**:
    ```bash
    python test_final.py
    ```
    * **Expected Behavior**: The script will automatically execute user registration, user login, and then use the obtained token to sequentially call the "Search by Species," "Query by Count," and "Manual Tag Management" APIs.
    * **Success Indication**: The command line will print the request information for each API and the successful JSON response, concluding with a summary showing all test cases as `PASS ✅`.

2.  **Test the Delete Functionality (Dangerous Operation)**:
    ```bash
    python test_final.py --delete --force
    ```
    * **Expected Behavior**: The script will bypass the standard flow, log in directly, and call the delete file API. The `--force` flag will skip the interactive confirmation.
    * **Success Indication**: A successful JSON message for the deletion is returned. You can subsequently check the OSS console and the Tablestore console to confirm that the corresponding file and data have been removed.

3.  **Test the Search by File Functionality**:
    ```bash
    python test_final.py --upload
    ```
    * **Expected Behavior**: The script will log in, then upload the image specified in `IMAGE_FILE_PATH`, and return links to other files in the database that contain similar tags.
    * **Success Indication**: A JSON response containing the `links` of similar files is returned.

## Part 2: Frontend UI Testing (via npm)

This section will start a local web server to run your Vue.js user interface and test all functionalities through a browser.

### 2.1 Environment Preparation

1.  **Install Node.js**: Ensure the LTS version of Node.js is installed on your computer. This will automatically install `npm`.
2.  **Install Vue CLI**: If not already installed, run `npm install -g @vue/cli` in your command line.
3.  **Get the Frontend Code**: Ensure you have the complete `birdtag-ui` project folder, which includes the `package.json` file.

### 2.2 Install Project Dependencies

1.  In your command line/terminal, navigate to the root directory of the `birdtag-ui` project.
2.  Run the following command to install all dependencies defined in `package.json` (e.g., Vue, Axios, etc.):
    ```bash
    npm install -g @vue/cli
    ```
    * This process may take a few minutes.
3.  npm install axios

### 2.3 Start and Conduct Frontend Testing

1.  In the command line, within the `birdtag-ui` project, run the following command to start the local development server:
    ```bash
    npm run serve
    ```
2.  After it starts successfully, the command line will display a `Local` address, typically `http://localhost:8080/`.
3.  Open this address in your browser (using an **Incognito/Private Window** is recommended).
4.  **Begin Testing**:
    * **Register/Login**: In the "User Authentication" module, enter an email and password, and click the "Register" and "Login" buttons respectively. Observe the "API Response" area and the notifications in the top-right corner.
    * **Query**: After a successful login, enter a bird species name or a JSON query in the "File Query" module and click the corresponding search buttons.
    * **Search by File**: Select a local image file and then click "Upload File & Search".
    * **File Management**: Enter a real original file URL and a tag to modify, then click the "Add/Remove Tag" buttons. Enter another URL and click the "Delete File" button (note that a confirmation dialog will appear).
    * **Verification**: For every action, carefully observe the "API Response" area to see if the expected content is returned (whether it's success data or a user-friendly error message), and check if the corresponding "Success" or "Failure" notification appears in the top-right corner.