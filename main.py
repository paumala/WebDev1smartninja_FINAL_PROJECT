#!/usr/bin/env python
import os
import jinja2
import webapp2
from models import Message
from google.appengine.api import users
import json
from google.appengine.api import urlfetch

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=False)


class BaseHandler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        return self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        return self.write(self.render_str(template, **kw))

    def render_template(self, view_filename, params=None):
        if not params:
            params = {}

        user = users.get_current_user()
        params["user"] = user

        if user:
            logged_in = True
            logout_url = users.create_logout_url('/')
            params["logout_url"] = logout_url
        else:
            logged_in = False
            login_url = users.create_login_url('/')
            params["login_url"] = login_url
        params["logged_in"] = logged_in

        template = jinja_env.get_template(view_filename)
        return self.response.out.write(template.render(params))


class HomeHandler(BaseHandler):
    def get(self):
        return self.render_template("home.html")


class AboutHandler(BaseHandler):
    def get(self):
        return self.render_template("about.html")


class MessagesHandler(BaseHandler):
    def get(self):
        messages = Message.query(Message.deleted == False).fetch()

        params = {"messages": messages}

        return self.render_template("messages.html", params=params)

    def post(self):

        user = users.get_current_user()

        if not user:
            return self.write("You are not logged in!")

        author = self.request.get("name")
        email = self.request.get("email")
        message = self.request.get("message")

        if not author:
            author = "Anonymous"

        if "<script>" in message:  # One way to fight JS injection
            return self.write("Can't hack me! Na na na na :)")

        msg_object = Message(author_name=author, email=email, message=message.replace("<script>", ""))  # another way to fight JS injection
        msg_object.put()  # save message into database

        return self.redirect_to("messages-site")  # see name in route


class MessageEditHandler(BaseHandler):
    def get(self, message_id):
        message = Message.get_by_id(int(message_id))

        params = {"message": message}

        return self.render_template("message_edit.html", params=params)

    def post(self, message_id):
        message = Message.get_by_id(int(message_id))

        text = self.request.get("message")
        message.message = text
        message.put()

        return self.redirect_to("messages-site")


class MessageDeleteHandler(BaseHandler):
    def get(self, message_id):
        message = Message.get_by_id(int(message_id))

        params = {"message": message}

        return self.render_template("message_delete.html", params=params)

    def post(self, message_id):
        message = Message.get_by_id(int(message_id))

        message.deleted = True  # fake delete
        message.put()

        return self.redirect_to("messages-site")

class WeatherHandler(BaseHandler):
    def get(self):

        cities = ["Split", "Zagreb", "Rijeka", "Osijek", "Zadar", "Dubrovnik", "Sibenik"]
        w_info = []

        for city in cities:
            url = "http://api.openweathermap.org/data/2.5/weather?q=" + city + ",hr&units=metric&appid=c5d1617f33c3ba2a7ea810d3f3fb3095"
            result = urlfetch.fetch(url)
            weather_info = json.loads(result.content)
            w_info.append(weather_info)

        params = {"weather_info" : w_info}

        return self.render_template("weather.html", params)

app = webapp2.WSGIApplication([
    webapp2.Route('/', HomeHandler),
    webapp2.Route('/about', AboutHandler, name="about-site"),
    webapp2.Route('/messages', MessagesHandler, name="messages-site"),
    webapp2.Route('/weather', WeatherHandler, name="weather-site"),
    webapp2.Route('/message/<message_id:\d+>/edit', MessageEditHandler, name="message-edit"),
    webapp2.Route('/message/<message_id:\d+>/delete', MessageDeleteHandler, name="message-delete")
], debug=True)
