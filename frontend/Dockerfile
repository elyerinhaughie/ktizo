FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN rm -f package-lock.json && npm install --no-optional || npm install

# Copy application
COPY . .

# Expose port
EXPOSE 5173

# Run the development server
CMD ["npm", "run", "dev"]
