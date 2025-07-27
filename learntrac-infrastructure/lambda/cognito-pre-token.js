exports.handler = async (event) => {
    console.log('Pre-token generation trigger:', JSON.stringify(event, null, 2));
    
    // Get user groups
    const groups = event.request.groupConfiguration.groupsToOverride || [];
    
    // Map groups to permissions
    const permissions = [];
    
    if (groups.includes('admins')) {
        permissions.push(
            'TRAC_ADMIN',
            'TICKET_ADMIN',
            'WIKI_ADMIN',
            'MILESTONE_ADMIN',
            'LEARNING_ADMIN'
        );
    }
    
    if (groups.includes('instructors')) {
        permissions.push(
            'TICKET_CREATE',
            'TICKET_MODIFY',
            'WIKI_CREATE',
            'WIKI_MODIFY',
            'LEARNING_INSTRUCT',
            'LEARNING_MENTOR'
        );
    }
    
    if (groups.includes('students')) {
        permissions.push(
            'TICKET_VIEW',
            'WIKI_VIEW',
            'TICKET_CREATE',
            'LEARNING_PARTICIPATE',
            'LEARNING_PRACTICE'
        );
    }
    
    // Add custom claims
    event.response = {
        claimsOverrideDetails: {
            claimsToAddOrOverride: {
                'custom:permissions': permissions.join(','),
                'custom:groups': groups.join(',')
            }
        }
    };
    
    return event;
};