FROM node:12

WORKDIR /app

COPY package*.json ./

RUN npm install -g @angular/cli @angular-devkit/build-angular && npm install && npm update

EXPOSE 4200