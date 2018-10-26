# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import sqlalchemy as sa

from h.models import Group, User
from h.models.group import ReadableBy
from h.util import group as group_util


class GroupService(object):

    def __init__(self, session, user_fetcher):
        """
        Create a new groups service.

        :param session: the SQLAlchemy session object
        :param user_fetcher: a callable for fetching users by userid
        :param publish: a callable for publishing events
        """
        self.session = session
        self.user_fetcher = user_fetcher

    def fetch(self, pubid):
        """Fetch a group by ``pubid``"""

        return self.session.query(Group).filter_by(pubid=pubid).one_or_none()

    def fetch_by_groupid(self, groupid):
        """
        Return a group with the given ``groupid`` combination or None

        :param groupid:     String in groupid format, e.g. ``group:foo@bar.com``
                            See :mod:`~h.models.group.Group`
        :raises ValueError: if ``groupid`` is not a valid groupid
                            see :func:`h.util.group.split_groupid`
        :rtype:             `~h.models.group.Group` or None
        """

        parts = group_util.split_groupid(groupid)
        authority = parts['authority']
        authority_provided_id = parts['authority_provided_id']

        return (self.session.query(Group).filter_by(authority=authority)
                                         .filter_by(authority_provided_id=authority_provided_id)
                                         .one_or_none())

    def groupids_readable_by(self, user):
        """
        Return a list of pubids for which the user has read access.

        If the passed-in user is ``None``, this returns the list of
        world-readable groups.

        :type user: `h.models.user.User`
        """
        readable = (Group.readable_by == ReadableBy.world)

        if user is not None:
            readable_member = sa.and_(Group.readable_by == ReadableBy.members, Group.members.any(User.id == user.id))
            readable = sa.or_(readable, readable_member)

        return [record.pubid for record in self.session.query(Group.pubid).filter(readable)]

    def groupids_created_by(self, user):
        """
        Return a list of pubids which the user created.

        If the passed-in user is ``None``, this returns an empty list.

        :type user: `h.models.user.User` or None
        """
        if user is None:
            return []

        return [g.pubid for g in self.session.query(Group.pubid).filter_by(creator=user)]


def groups_factory(context, request):
    """Return a GroupService instance for the passed context and request."""
    user_service = request.find_service(name='user')
    return GroupService(session=request.db,
                        user_fetcher=user_service.fetch)
