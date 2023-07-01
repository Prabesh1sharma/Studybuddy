from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from django.contrib.auth import authenticate, login, logout

from django.http import HttpResponse
from .models import Room, Topic, Message, User
from .forms import RoomForm, UserForm, MyUserCreationForm
import os
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from .models import UserProfile, Message

from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage

from .tokens import account_activation_token
from django.utils.html import format_html


# Create your views here.

#rooms = [
#    {'id':1, 'name': 'Lets learn python!'},
#    {'id':2, 'name': 'Design with me'},
#    {'id':3, 'name': 'Frontend developers'},
#]

def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except:
            messages.error(request, 'User does not exist')
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username OR password does not exist')

    context = {'page': page}
    return render(request, 'base/login_register.html', context)

def logoutUser(request):
    logout(request)
    return redirect('home')

def activate(request, uidb64, token):
    # User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()

        messages.success(request, 'Thank you for your email confirmation. Now you can login your account.')
        return redirect('login')
    else:
        messages.error(request, 'Activation link is invalid!')
    
    return redirect('home')

def activateEmail(request, user, to_email):
    mail_subject = 'Activate your user account.'
    message = render_to_string('base/template_activate_account.html', {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(request,format_html(f'Dear <b>{user.username}</b>, please go to you email <b>{to_email}</b> inbox and click on \
            received activation link to confirm and complete the registration. <b>Note:</b> Check your spam folder).'))
    else:
        messages.error(request, f'Problem sending confirmation email to {to_email}, check if you typed it correctly.')

def registerPage(request):
    form = MyUserCreationForm()
    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user= form.save(commit=False)
            user.is_active=False
            user.username = user.username.lower()
            user.save()
            activateEmail(request, user, form.cleaned_data.get('email'))
            # UserProfile.objects.create(user=user)
            # login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'An error occured during registration')

    return render(request, 'base/login_register.html', {'form': form}) 

def home(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    rooms = Room.objects.filter(
        Q(topic__name__icontains=q) |
        Q(name__icontains=q) |
        Q(description__icontains=q)

        )
    

    topics = Topic.objects.all()[0:5]
    room_count = rooms.count()
    room_messages = Message.objects.filter(Q(room__topic__name__icontains=q))

    context = {'rooms': rooms, 'topics': topics,
                'room_count': room_count, 'room_messages':room_messages}
    return render(request, 'base/home.html', context)

def room(request, pk):
    room = Room.objects.get(id=pk)
    room_messages = room.message_set.all()
    participants = room.participants.all()
    
    if request.method == 'POST':
        message = Message.objects.create(
            user=request.user,
            room = room,
            body = request.POST.get('body')
        )
        room.participants.add(request.user)
        return redirect('room', pk=room.id)
    

    context = {'room':room, 'room_messages': room_messages,
               'participants':participants}
    return render(request, 'base/room.html', context)

from .models import UserProfile

def userProfile(request, pk):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    room_messages = Message.objects.filter(Q(room__topic__name__icontains=q))
    
    topics = Topic.objects.all()
    is_following = False

    if request.user.is_authenticated:
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if user_profile:
            is_following = user_profile.followers.filter(id=pk).exists()  

    context = {
        'user': user,
        'rooms': rooms,
        'room_messages': room_messages,
        'topics': topics,
        'is_following': is_following,
        'followers_count': user_profile.followers.count(),
        'following_count': user_profile.following.count(),
        'followers_list': user_profile.followers.all(),
        'following_list': user_profile.following.all()
    }
    return render(request, 'base/profile.html', context)





@login_required(login_url= 'login')
def createRoom(request):
    form = RoomForm()
    topics = Topic.objects.all()
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)

        Room.objects.create(
            host=request.user,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
        )
        return redirect('home')

        # form = RoomForm(request.POST)
        # if form.is_valid():
        #     room = form.save(commit=False)
        #     room.host = request.user
        #     form.save()
           
    
    context = {'form': form, 'topics':topics}
    return render(request, 'base/room_form.html', context)

@login_required(login_url= 'login')
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)
    topics = Topic.objects.all()

    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')


    if request.method == 'POST':
            topic_name = request.POST.get('topic')
            topic, created = Topic.objects.get_or_create(name=topic_name)
            room.name = request.POST.get('name')
            room.topic = topic
            room.description = request.POST.get('description')
            room.save()
            return redirect('home')


    context = {'form': form, 'topics':topics, 'room': room}
    return render(request, 'base/room_form.html', context)

@login_required(login_url= 'login')
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)
    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')
    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj':room})




@login_required(login_url= 'login')
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)
    if request.user != message.user:
        return HttpResponse('You are not allowed here!!')
    if request.method == 'POST':
        message.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj':message})

@login_required(login_url= 'login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)

    context = {'form': form}
    return render(request, 'base/update-user.html', context)

def topicsPage(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    topics = Topic.objects.filter(name__icontains=q)
    return render(request, 'base/topics.html', {'topics': topics})

@login_required(login_url='login')
def messengerPage(request, pk):
    
    user = User.objects.get(id=pk)
    logged_in_users = User.objects.filter(is_active=True)
    user_messages = user.received_messages.all()
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        recipient = User.objects.get(id=recipient_id)
        message_user = Message.objects.create(
            user=request.user,
            recipient=recipient,
            body=request.POST.get('body')
        )
        return redirect('messenger', pk=message_user.recipient.id)

    context = {
        'logged_in_users': logged_in_users,
        'user': user,
        'user_messages': user_messages
    }
    return render(request, 'base/messenger.html', context)

def activityPage(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    room_messages = Message.objects.filter(Q(room__topic__name__icontains=q))
    return render(request, 'base/activity.html', {'room_messages': room_messages})


def deleteAvatar(request):
    user = request.user
    if request.method == 'POST':
        # Delete the avatar file from the static directory
        avatar_path = os.path.join(settings.BASE_DIR, 'static', user.avatar.name)
        if os.path.exists(avatar_path):
            os.remove(avatar_path)

        # Set the avatar field to the default image
        user.avatar = 'avatar.svg'
        user.save()

        return redirect('user-profile', pk=user.id)

    return render(request, 'base/delete_avatar.html')
    


@login_required(login_url='login')    
def follow(request, pk):
    user_to_follow = User.objects.get(id=pk)
   
    if request.method == 'POST':
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_profile.followers.add(user_to_follow)
        
    return redirect('user-profile', pk=pk)

@login_required(login_url='login')     
def unfollow(request, pk):
    user_to_unfollow = User.objects.get(id=pk)
   
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.followers.remove(user_to_unfollow)
        
    return redirect('user-profile', pk=pk)


# @login_required(login_url='login')
# def messengerPage(request, pk):
#     user = User.objects.get(id=pk)
#     logged_in_users = User.objects.filter(is_active=True)
#     user_messages = user.received_messages.all()
#     if request.method == 'POST':
#         recipient_id = request.POST.get('recipient_id')
#         recipient = User.objects.get(id=recipient_id)
#         message = Message.objects.create(
#             user=request.user,
#             recipient=recipient,
#             body=request.POST.get('body')
#         )
#         return redirect('messenger', pk=message.recipient.id)

#     context = {
#         'logged_in_users': logged_in_users,
#         'user': user,
#         'user_messages': user_messages
#     }
#     return render(request, 'base/messenger.html', context)




