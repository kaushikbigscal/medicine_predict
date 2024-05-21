# Get the python image
FROM python:3.10

# Switch to app directory
WORKDIR /app
COPY . /app

# Copy the requirements in to the app
COPY requirements.txt ./

# Install dependencies
RUN pip install -r requirements.txt

# Copy everything else
EXPOSE 5000

#Run the python script
CMD [ "python", "./main.py"]