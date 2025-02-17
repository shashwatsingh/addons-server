from django.conf import settings
from django.core.exceptions import PermissionDenied
from django import http, shortcuts
from django.db.transaction import non_atomic_requests
from django.utils.crypto import constant_time_compare
from django.utils.translation import ugettext
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import condition

from csp.decorators import csp as set_csp

import olympia.core.logger

from olympia.access import acl
from olympia.amo.decorators import use_primary_db
from olympia.amo.decorators import json_view
from olympia.amo.urlresolvers import reverse
from olympia.amo.utils import HttpResponseXSendFile, render, urlparams
from olympia.files.decorators import (
    compare_file_view, etag, file_view, file_view_token, last_modified)
from olympia.files.file_viewer import extract_file
from olympia.lib.cache import Message, Token
from olympia.versions.models import Version

from .models import FileUpload
from . import forms


log = olympia.core.logger.getLogger('z.addons')


def setup_viewer(request, file_obj):
    addon = file_obj.version.addon
    data = {
        'file': file_obj,
        'version': file_obj.version,
        'addon': addon,
        'status': False,
        'selected': {},
        'validate_url': ''
    }
    is_user_a_reviewer = acl.is_reviewer(request, addon)

    if (is_user_a_reviewer or acl.check_addon_ownership(
            request, addon, dev=True, ignore_disabled=True)):

        data['validate_url'] = reverse('devhub.json_file_validation',
                                       args=[addon.slug, file_obj.id])
        data['automated_signing'] = file_obj.automated_signing

        if file_obj.has_been_validated:
            data['validation_data'] = file_obj.validation.processed_validation

    if is_user_a_reviewer:
        data['file_link'] = {
            'text': ugettext('Back to review'),
            'url': reverse('reviewers.review', args=[addon.slug])
        }
    else:
        data['file_link'] = {
            'text': ugettext('Back to add-on'),
            'url': reverse('addons.detail', args=[addon.pk])
        }
    return data


@never_cache
@json_view
@file_view
@non_atomic_requests
def poll(request, viewer):
    return {'status': viewer.is_extracted(),
            'msg': [Message('file-viewer:%s' % viewer).get(delete=True)]}


def check_compare_form(request, form):
    if request.method == 'POST':
        if form.is_valid():
            left = form.cleaned_data['left']
            right = form.cleaned_data.get('right')
            if right:
                url = reverse('files.compare', args=[left, right])
            else:
                url = reverse('files.list', args=[left])
        else:
            url = request.path
        return shortcuts.redirect(url)


@csrf_exempt
@file_view
@non_atomic_requests
@condition(etag_func=etag, last_modified_func=last_modified)
def browse(request, viewer, key=None, type='file'):
    form = forms.FileCompareForm(request.POST or None, addon=viewer.addon,
                                 initial={'left': viewer.file},
                                 request=request)
    response = check_compare_form(request, form)
    if response:
        return response

    data = setup_viewer(request, viewer.file)
    data['viewer'] = viewer
    data['poll_url'] = reverse('files.poll', args=[viewer.file.id])
    data['form'] = form

    if not viewer.is_extracted():
        extract_file(viewer)

    if viewer.is_extracted():
        data.update({'status': True, 'files': viewer.get_files()})
        key = viewer.get_default(key)
        if key not in data['files']:
            raise http.Http404

        viewer.select(key)
        data['key'] = key
        if (not viewer.is_directory() and not viewer.is_binary()):
            data['content'] = viewer.read_file()

    tmpl = 'files/content.html' if type == 'fragment' else 'files/viewer.html'
    return render(request, tmpl, data)


def browse_redirect(request, version_id):
    version = shortcuts.get_object_or_404(Version, pk=version_id)
    url_args = [version.current_file.id]

    file = request.GET.get('file')
    if file:
        url_args.extend(['file', file])
    url = reverse('files.list', args=url_args)

    return http.HttpResponseRedirect(url)


def compare_redirect(request, base_id, head_id):
    base_version = shortcuts.get_object_or_404(Version, pk=base_id)
    head_version = shortcuts.get_object_or_404(Version, pk=head_id)
    url_args = [base_version.current_file.id, head_version.current_file.id]

    file = request.GET.get('file')
    if file:
        url_args.extend(['file', file])

    url = reverse('files.compare', args=url_args)
    return http.HttpResponseRedirect(url)


@never_cache
@compare_file_view
@json_view
@non_atomic_requests
def compare_poll(request, diff):
    msgs = []
    for f in (diff.left, diff.right):
        m = Message('file-viewer:%s' % f).get(delete=True)
        if m:
            msgs.append(m)
    return {'status': diff.is_extracted(), 'msg': msgs}


@csrf_exempt
@compare_file_view
@condition(etag_func=etag, last_modified_func=last_modified)
@non_atomic_requests
def compare(request, diff, key=None, type='file'):
    form = forms.FileCompareForm(request.POST or None, addon=diff.addon,
                                 initial={'left': diff.left.file,
                                          'right': diff.right.file},
                                 request=request)
    response = check_compare_form(request, form)
    if response:
        return response

    data = setup_viewer(request, diff.left.file)
    data['diff'] = diff
    data['poll_url'] = reverse('files.compare.poll',
                               args=[diff.left.file.id,
                                     diff.right.file.id])
    data['form'] = form

    if not diff.is_extracted():
        extract_file(diff.left)
        extract_file(diff.right)

    if diff.is_extracted():
        data.update({'status': True,
                     'files': diff.get_files(),
                     'files_deleted': diff.get_deleted_files()})
        key = diff.left.get_default(key)
        if key not in data['files'] and key not in data['files_deleted']:
            raise http.Http404

        diff.select(key)
        data['key'] = key
        if diff.is_diffable():
            data['left'], data['right'] = diff.read_file()

    tmpl = 'files/content.html' if type == 'fragment' else 'files/viewer.html'
    return render(request, tmpl, data)


@file_view
@non_atomic_requests
def redirect(request, viewer, key):
    new = Token(data=[viewer.file.id, key])
    new.save()
    url = reverse('files.serve', args=[viewer, key])
    url = urlparams(url, token=new.token)
    return http.HttpResponseRedirect(url)


@set_csp(**settings.RESTRICTED_DOWNLOAD_CSP)
@file_view_token
@non_atomic_requests
def serve(request, viewer, key):
    """
    This is to serve files off of st.a.m.o, not standard a.m.o. For this we
    use token based authentication.
    """
    files = viewer.get_files()
    obj = files.get(key)
    if not obj:
        log.error(u'Couldn\'t find %s in %s (%d entries) for file %s' % (
                  key, list(files.keys())[:10], len(files.keys()),
                  viewer.file.id))
        raise http.Http404

    fobj = open(obj['full'], 'rb')

    response = http.FileResponse(
        fobj, as_attachment=True, content_type=obj['mimetype'])

    return response


@use_primary_db
def serve_file_upload(request, uuid):
    """
    This is to serve file uploads using authenticated download URLs. This is
    currently used by the "scanner" services.
    """
    upload = shortcuts.get_object_or_404(FileUpload, uuid=uuid)
    access_token = request.GET.get('access_token')

    if not access_token:
        log.error('Denying access to %s, no token.', upload.id)
        raise PermissionDenied

    if not constant_time_compare(access_token, upload.access_token):
        log.error('Denying access to %s, token invalid.', upload.id)
        raise PermissionDenied

    if not upload.path:
        log.info('Preventing access to %s, upload path is falsey.' % upload.id)
        return http.HttpResponseGone('upload path does not exist anymore')

    return HttpResponseXSendFile(request,
                                 upload.path,
                                 content_type='application/octet-stream')
