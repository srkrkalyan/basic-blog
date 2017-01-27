#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
from google.appengine.ext import db
import time
import hashlib

# Creates a reference to templates dir
template_dir = os.path.join(os.path.dirname(__file__),'templates')

#Creates a reference to jinja2 environment
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
				autoescape=True)

class Blog(db.Model):
	title = db.StringProperty(required = True)
	blog = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True, indexed=True)
	blog_id = db.IntegerProperty(required=True)
	user_id = db.IntegerProperty(required=True)
	likes_count = db.IntegerProperty()


class User(db.Model):
	user_id = db.IntegerProperty(required=True)
	user_name=db.StringProperty(required=True)
	password = db.StringProperty(required=True)
	email=db.StringProperty()


class Comment(db.Model):
	user_id=db.IntegerProperty(required=True)
	blog_id=db.IntegerProperty(required=True)
	user_name=db.StringProperty(required=True)
	comment=db.TextProperty(required=True)
	created = db.DateTimeProperty(auto_now_add = True)

class Like(db.Model):
	user_id=db.IntegerProperty(required=True)
	blog_id=db.IntegerProperty(required=True)
	like_flag = db.BooleanProperty(required=True)



class Handler(webapp2.RequestHandler):
	def write(self,*a,**kw):
		self.response.out.write(*a,**kw)

	def render_str(self,template,**params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self,template,**kw):
		self.write(self.render_str(template,**kw))

	def new_id(self,row_count):
		blog_id = 1000+row_count
		return blog_id

	def new_user_id(self,row_count):
		user_id = 5000+row_count
		return user_id

	def hashme(self,password):
		return hashlib.sha256(password).hexdigest()

	def validate_user_login(self,username,password):
		user_details = db.GqlQuery("select * from User where user_name= :1", username).get()
		if user_details.password == self.hashme(password):
			return True
		else:
			return False

	def get_current_user(self):
		if self.request.cookies.get('user_id'):
			cookie_value = self.request.cookies.get('user_id').split('|')[0]
			if cookie_value:
				if db.GqlQuery('select * from User where user_id='+str(cookie_value)).get():
					return cookie_value
				else:
					return None
		else:
			return None

	def get_current_blog(self):
		cookie_blog_id = self.request.cookies.get('blog_id')
		if cookie_blog_id:
			return cookie_blog_id
		else:
			return None

	def user_owns_blog(self,user_id,blog_id):
		print 'Blog Id:'+blog_id
		print db.GqlQuery("select * from Blog where blog_id="+blog_id).get().user_id
		if int(user_id) == db.GqlQuery("select * from Blog where blog_id="+blog_id).get().user_id:
			print 'Yes'
			return True
		else:
			return False

	def create_comment_id(self):
		comments = db.GqlQuery("select * from Comment").count()
		return comments+7000+1

class BlogHandler(Handler):
    def get(self):
    	cookie_value = self.request.cookies.get('user_id')
    	if (db.GqlQuery("select * from Blog").count()) > 0:
    		blogs = db.GqlQuery("select * from Blog order by created desc").fetch(limit=10)
    		self.render("blog_front.html",blogs=blogs,cookie_value=cookie_value)
    	else:
    		self.render("blog_front.html")

class SignUp(Handler):
	def get(self):
		# Setting a cookie in response header as soon as a request is received to sign up page
		users_count = db.GqlQuery("select * from User").count()
		user_id = self.new_user_id(users_count)
		cookie_value=str(user_id)+'|'+str(self.hashme(str(user_id)))
		self.response.headers.add_header('set-cookie','user_id=%s; path=/' % cookie_value)
		self.render("sign_up.html")
	def post(self,*args,**kw):
		username = self.request.get("username")
		password=self.request.get("password")
		verify_password = self.request.get("verify")
		email = self.request.get("email")
		users_count = db.GqlQuery("select * from User").count()
		user_id = self.new_user_id(users_count)
		if username and password and (password == verify_password):
			user_entry = User(user_name=username, password = self.hashme(password), user_id=user_id,email=email)
			user_entry.put()
			#time.sleep(2)
			self.redirect('/blog/welcome')
		elif username and (password != verify_password):
			error = "Password mismatch !!! Please retry"
			self.render("sign_up.html",username=username,password=password, verify_password=verify_password,error=error)
		else:
			error = "Both username and password required. Please give all required details"
			self.render("sign_up.html",username=username,password=password, verify_password=verify_password,error=error)			


class Login(Handler):
	# Render basic login form
	def get(self):
		cookie_value = self.request.cookies.get('user_id')
		if cookie_value:
			if db.GqlQuery('select * from User where user_id='+str(cookie_value.split('|')[0])).get():
				self.render("login.html", cookie_value=cookie_value.split('|')[0])
			else:
				self.render("login.html",cookie_value=None)
		else:
			self.render("login.html",cookie_value=None)
	
	# User submits login form data. 
	# If user authentication successful, navigate to welcome page with list of all his blogs
	def post(self):
		username = self.request.get("username")
		password=self.request.get("password")
		user_entry = db.GqlQuery("select * from User where user_name= :1", username).get()
		# This needs to be commented before deployment
		#time.sleep(2)
		#print user_entry.user_name
		if username and password:
			if user_entry:
				if self.validate_user_login(username,password):
					cookie_value=str(user_entry.user_id)+'|'+str(self.hashme(str(user_entry.user_id)))
					self.response.headers.add_header('set-cookie','user_id=%s; path=/' % cookie_value)
					self.redirect('/blog/welcome')
				else:
					error = "Either user or password is incorrect. Please check again !!!"
					self.render("login.html", username=username,error=error)
			else:
				error="User does not exist"
				self.render("login.html", username=username,error=error)
		else:
			error = "Both user name and password required"
			self.render("login.html", username=username,error=error)

class Logout(Handler):
	def get(self):
		self.response.headers.add_header('set-cookie','user_id=; path=/')
		self.response.headers.add_header('set-cookie','blog_id=; path=/')
		self.redirect('/blog')

class Welcome(Handler):
	def get(self):
		cookie_value = self.request.cookies.get('user_id')
		user_id=cookie_value.split('|')[0]
		username=db.GqlQuery("select * from User where user_id="+user_id).get().user_name
		blogs = db.GqlQuery("select * from Blog where user_id="+user_id+" order by created desc").fetch(limit=10)
		self.render("welcome.html",username=username,blogs=blogs,cookie_value=cookie_value)

class NewPostHandler(Handler):
	def get(self):
		cookie_blog_id = self.request.cookies.get('blog_id')
		if cookie_blog_id:
			blog_details  = db.GqlQuery("select * from Blog where blog_id="+str(cookie_blog_id)).get()
			self.render("new_post.html",title=blog_details.title,blog=blog_details.blog)
		else:
			self.render("new_post.html")
	def post(self,*args, **kw):
		# Fetch the user id by reading cokie value
		#cookie_value = self.request.cookies.get('user_id')
		#user_id=cookie_value.split('|')[0]
		user_id=self.get_current_user()
		username=db.GqlQuery("select * from User where user_id="+user_id).get().user_name
		title=self.request.get("subject")
		blog=self.request.get("content")
		error = "Both title and blog should present"
		if title and blog:
			cookie_blog_id = self.request.cookies.get('blog_id')
			if cookie_blog_id:
				blog_entry = db.GqlQuery("select * from Blog where blog_id="+str(cookie_blog_id)).get()
				blog_entry.title = title
				blog_entry.blog = blog
				blog_entry.user_id = int(user_id)
				blog_entry.put()
				redirect_url = '/blog/'+str(cookie_blog_id)
				self.redirect(redirect_url)
			else:
				blogs_count = db.GqlQuery("select * from Blog").count()
				blog_id = self.new_id(blogs_count)
				blog_entry = Blog(title=title, blog=blog, blog_id=blog_id, user_id=int(user_id))
				blog_entry.put()
				redirect_url = '/blog/'+str(blog_id)
				self.redirect(redirect_url)
		else:
			self.render("new_post.html", title=title, blog=blog, error=error)

class PermaLink(Handler):
	def get(self,blog_id):
		# Get the latest blog entry from Blog table using newly generated blog_id. 
		# I can do this by 'select * from Blog order by created desc'.fetch(limit=1)
		
		time.sleep(2)
		blog = db.GqlQuery("select * from Blog where blog_id ="+ str(blog_id)).get()
		
		
		# Rendering Permalink page with details of title (Subject) and Blog (Content)
		self.render("blog_details.html",title=blog.title,blog=blog.blog)
	
	def post(self,*a,**kw):
		self.render("blog_details.html")

class EditBlog(Handler):
	def get(self,blog_id):
		user_id = self.get_current_user()
		if user_id:
			if (db.GqlQuery("select * from Blog where blog_id="+blog_id).get().user_id) == int(user_id):
				blog = db.GqlQuery("select * from Blog where blog_id="+blog_id).get()
				self.response.headers.add_header('set-cookie','blog_id=%s; path=/' % blog_id)
				#self.render("new_post.html",title=blog.title,blog=blog.blog)
				self.redirect("/blog/newpost")
			else:
				self.write("Edit not possible. You dont own this blog")


class DeleteBlog(Handler):
	def get(self,blog_id):
		user_id = self.get_current_user()
		if user_id:
			if (db.GqlQuery("select * from Blog where blog_id="+blog_id).get().user_id) == int(user_id):
				blog=db.GqlQuery("select * from Blog where blog_id="+blog_id).get()
				blog.delete()
				self.redirect("/blog")
			else:
				self.write("Delete not possible. You dont own this blog")

class LikeBlog(Handler):
	def get(self,blog_id):
		user_id = self.get_current_user()
		if user_id:
			if self.user_owns_blog(user_id,blog_id):
				self.write("You cant like your own blog")
			elif db.GqlQuery("select * from Like where user_id="+ user_id+" and blog_id="+ blog_id).get():
				self.redirect("/blog")
			else:
				#like_entry=db.GqlQuery("select * from Like where user_id="+ user_id+" and blog_id="+ blog_id).get()
				like_entry=Like(user_id=int(user_id), blog_id=int(blog_id), like_flag=True)
				like_entry.put()
				blog_entry = db.GqlQuery("select * from Blog where blog_id="+str(blog_id)).get()
				likes_count=db.GqlQuery("select * from Like where blog_id="+ blog_id+" and like_flag = True").count()
				blog_entry.likes_count = likes_count
				blog_entry.put()
				self.redirect("/blog")
				'''if likes_count == None:
					blog_entry.likes_count = 0
					blog_entry.likes_count = int(blog_entry.likes_count)+1
					blog_entry.put()
					# comment before deployment
					time.sleep(2)
					self.redirect("/blog")
				else:
					blog_entry.likes_count = int(blog_entry.likes_count)+1
					blog_entry.put()
					# comment before deployment
					time.sleep(2)
					self.redirect("/blog") '''
		else:
			self.write("You need to login to like a blog")

class UnLikeBlog(Handler):
	def get(self,blog_id):
		user_id = self.get_current_user()
		if db.GqlQuery("select * from Like where user_id="+ user_id+" and blog_id="+ blog_id).get():
			like_entry=db.GqlQuery("select * from Like where user_id="+ user_id+" and blog_id="+ blog_id).get()
			like_entry.like_flag=False
			like_entry.put()
			self.redirect("/blog")



class CommentBlog(Handler):
	def get(self,blog_id):
		user_id = self.get_current_user()
		if user_id:
			if not self.user_owns_blog(user_id,blog_id):
				comments=db.GqlQuery("select * from Comment where blog_id="+ blog_id+" order by created desc").fetch(limit=100)
				blog_entry = db.GqlQuery("select * from Blog where blog_id="+ blog_id).get()
				self.render("comment.html",comments=comments, blog=blog_entry)
			else:
				self.write("You can't comment on your blog")
		else:
			self.write("Please login to comment a blog")
				
	def post(self,blog_id):
		user_id = self.get_current_user()
		comment_id = self.create_comment_id()
		user_name = db.GqlQuery("select * from User where user_id="+ str(user_id)).get().user_name
		comment=self.request.get('comment')
		if comment:
			comment_entry=Comment(blog_id=int(blog_id), user_id=int(user_id), user_name=str(user_name), comment=comment)
			comment_entry.put()
			# Comment this before deployment
			time.sleep(2)
			self.redirect('/blog/'+str(blog_id)+'/commentblog')
		else:
			time.sleep(2)
			self.redirect('/blog/'+str(blog_id)+'/commentblog')


app = webapp2.WSGIApplication([
	('/blog/signup', SignUp),
    ('/blog', BlogHandler),
    ('/blog/newpost', NewPostHandler),
    ('/blog/([0-9]+)', PermaLink),
    ('/blog/welcome', Welcome),
    ('/blog/login', Login),
    ('/blog/logout', Logout),
    ('/blog/([0-9]+)/editblog', EditBlog),
    ('/blog/([0-9]+)/deleteblog',DeleteBlog),
    ('/blog/([0-9]+)/likeblog', LikeBlog),
    ('/blog/([0-9]+)/commentblog', CommentBlog),
    ('/blog/([0-9]+)/unlikeblog', UnLikeBlog),
], debug=True)
