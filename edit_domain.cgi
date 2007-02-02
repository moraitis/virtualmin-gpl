#!/usr/local/bin/perl
# edit_domain.cgi
# Display details of a domain for editing

require './virtual-server-lib.pl';
use POSIX;
&ReadParse();
$d = &get_domain($in{'dom'});
$d || &error($text{'edit_egone'});
&can_config_domain($d) || &error($text{'edit_ecannot'});
if ($d->{'parent'}) {
	$parentdom = &get_domain($d->{'parent'});
	}
if ($d->{'alias'}) {
	$aliasdom = &get_domain($d->{'alias'});
	}
if ($d->{'subdom'}) {
	$subdom = &get_domain($d->{'subdom'});
	}
$tmpl = &get_template($d->{'template'});
&ui_print_header(&domain_in($d), $aliasdom ?  $text{'edit_title3'} :
				 $subdom ?    $text{'edit_title4'} :
				 $parentdom ? $text{'edit_title2'} :
					      $text{'edit_title'}, "");

@tds = ( "width=30%" );
print &ui_form_start("save_domain.cgi", "post");
print &ui_hidden("dom", $in{'dom'}),"\n";
print &ui_table_start($text{'edit_header'}, "width=100%", 4);

# Domain name, with link
print &ui_table_row($text{'edit_domain'},
	$d->{'web'} ? "<tt><a href=http://$d->{'dom'}/>$d->{'dom'}</a></tt>"
		    : "<tt>$d->{'dom'}</tt>", undef, \@tds);

# Username
print &ui_table_row($text{'edit_user'},
		    "<tt>$d->{'user'}</tt>",
		    undef, \@tds);

# Group name
print &ui_table_row($text{'edit_group'},
		    ($d->{'unix'} || $d->{'parent'}) && $d->{'group'} ?
			"<tt>$d->{'group'}</tt>" : $text{'edit_nogroup'},
		    undef, \@tds);

if (!$aliasdom) {
	# Only show database name/count for non-alias domains
	@dbs = &domain_databases($d);
	print &ui_table_row($text{'edit_dbs'},
		@dbs > 0 ? scalar(@dbs) : $text{'edit_nodbs'},
		undef, \@tds);
	}
else {
	print &ui_table_row(" ", " ");	# End of row
	}

# Show creator
print &ui_table_row($text{'edit_created'},
	$d->{'creator'} ? &text('edit_createdby',
				&make_date($d->{'created'}), $d->{'creator'})
			: &make_date($d->{'created'}),
	undef, \@tds);

# Show username prefix, with option to change
if (!$aliasdom) {
	@users = &list_domain_users($d, 1, 1, 1, 1);
	$msg = $tmpl->{'append_style'} == 0 || $tmpl->{'append_style'} == 1 ||
	       $tmpl->{'append_style'} == 5 ? 'edit_prefix' : 'edit_suffix';
	print &ui_table_row($text{$msg},
		@users ? "<tt>$d->{'prefix'}</tt> (".
			  &text('edit_noprefix', scalar(@users)).")"
		       : &ui_textbox("prefix", $d->{'prefix'}, 30),
		undef, \@tds);
	}
else {
	print &ui_table_row(" ", " ");  # End of row
	}

# Show active template
foreach $t (&list_templates()) {
	next if ($t->{'deleted'});
	next if (($d->{'parent'} && !$d->{'alias'}) && !$t->{'for_sub'});
	next if (!$d->{'parent'} && !$t->{'for_parent'});
	next if (!&master_admin() && !&reseller_admin() && !$t->{'for_users'});
	next if ($d->{'alias'} && !$t->{'for_alias'});
	next if (!&can_use_template($t));
	push(@cantmpls, $t);
	$gottmpl = 1 if ($t->{'id'} == $tmpl->{'id'});
	}
push(@cantmpls, $tmpl) if (!$gottmpl);
print &ui_table_row($text{'edit_tmpl'},
		    &ui_select("template", $tmpl->{'id'},
			[ map { [ $_->{'id'}, $_->{'name'} ] } @cantmpls ]),
		    undef, \@tds);

# Show reseller
print &ui_table_row($text{'edit_reseller'},
		    $d->{'reseller'} ? "<tt>$d->{'reseller'}</tt>"
				     : $text{'edit_noreseller'},
		    undef, \@tds);

if (!$aliasdom) {
	# Show IP-related options
	if ($d->{'reseller'}) {
		$resel = &get_reseller($d->{'reseller'});
		if ($resel) {
			$reselip = $resel->{'acl'}->{'defip'};
			}
		}
	print &ui_table_row($text{'edit_ip'},
		  "<tt>$d->{'ip'}</tt> ".
		  ($d->{'virt'} ? $text{'edit_private'} :
		   $d->{'ip'} eq $reselip ? &text('edit_rshared',
						  "<tt>$resel->{'name'}</tt>") :
					    $text{'edit_shared'}), 3,
		  \@tds);

	if ($d->{'virt'}) {
		# Got a virtual IP .. show option to remove
		local $iface = &get_address_iface($d->{'ip'});
		$ipfield = &ui_radio("virt", 1,
		    [ [ 0, $text{'edit_virtoff'} ],
		      [ 1, &text('edit_virton', "<tt>$iface</tt>") ] ]);
		}
	elsif ($config{'all_namevirtual'}) {
		# Always name-based, but IP can be changed
		$ipfield = &ui_textbox("ip", $d->{'ip'}, 15);
		}
	elsif (!&can_use_feature("virt")) {
		# Not allowed to add virtual IP
		$ipfield = $text{'edit_virtnone'};
		}
	else {
		# No IP .. show option to add
		$ipfield = &ui_oneradio("virt", 0, $text{'edit_virtnone'}, 1);
		if ($tmpl->{'ranges'} ne "none") {
			# Can do automatic allocation
			local %racl = $d->{'reseller'} ?
				&get_reseller_acl($d->{'reseller'}) : ();
			local $alloc = $racl{'ranges'} ?
				&free_ip_address(\%racl) :
				&free_ip_address($tmpl);
			if ($alloc) {
				$ipfield .= &ui_oneradio("virt", 1,
					&text('edit_alloc', $alloc), 0);
				}
			else {
				# None left!
				$ipfield .= $text{'form_noalloc'};
				}
			}
		else {
			# Use must enter IP
			$ipfield .= &ui_oneradio("virt", 1,
						 $text{'edit_virtalloc'}, 0).
				    " ".&ui_textbox("ip", undef, 15);
			}
		}
	print &ui_table_row($text{'edit_virt'}, $ipfield, 3, \@tds);
	}

if (!$aliasdom && $d->{'dir'}) {
	# Show home directory
	print &ui_table_row($text{'edit_home'},
			    "<tt>$d->{'home'}</tt>", 3, \@tds);
	}

if ($d->{'proxy_pass_mode'} && $d->{'proxy_pass'} && $d->{'web'}) {
	# Show forwarding / proxy destination
	print &ui_table_row($text{'edit_proxy'.$d->{'proxy_pass_mode'}},
			    "<tt>$d->{'proxy_pass'}</tt>", 3, \@tds);
	}

# Show description
print &ui_table_row($text{'edit_owner'},
		    &ui_textbox("owner", $d->{'owner'}, 50), 3, \@tds);

if ($aliasdom) {
	# Show link to aliased domain
	print &ui_table_row($text{'edit_aliasto'},
			    "<a href='edit_domain.cgi?dom=$d->{'alias'}'>".
			    "$aliasdom->{'dom'}</a>", 3, \@tds);
	}
elsif (!$parentdom) {
	# Show owner's email address and password
	print &ui_table_row($text{'edit_email'},
		$d->{'unix'} ? &ui_opt_textbox("email", $d->{'email'}, 30,
					       $text{'edit_email_def'})
			     : &ui_textbox("email", $d->{'email'}, 30), 3,
		\@tds);

	print &ui_table_row($text{'edit_passwd'},
		&ui_opt_textbox("passwd", undef, 20,
				$text{'edit_lv'}." ".&show_password_popup($d),
				$text{'edit_set'}), 3,
		\@tds);
	}
else {
	# Show link to parent domain
	print &ui_table_row($text{'edit_parent'},
			    "<a href='edit_domain.cgi?dom=$d->{'parent'}'>".
			    "$parentdom->{'dom'}</a>", 3, \@tds);
	}

# Show any alias domains
@aliasdoms = &get_domain_by("alias", $d->{'id'});
if (@aliasdoms) {
	print &ui_table_row($text{'edit_aliasdoms'},
		&domains_list_links(\@aliasdoms, "alias", $d->{'dom'}), 3,
		\@tds);
	}

# Show any sub-servers
@subdoms = &get_domain_by("parent", $d->{'id'}, "alias", undef);
if (@subdoms) {
	print &ui_table_row($text{'edit_subdoms'},
		&domains_list_links(\@subdoms, "parent", $d->{'dom'}), 3,
		\@tds);
	}

print &ui_table_end();
if (!$parentdom) {
	# Start of collapsible section for limits
	print &ui_hidden_table_start($text{'edit_limitsect'}, "width=100%", 2,
				     "limits", 0);
	}

# Show user and group quota editing inputs
if (&has_home_quotas() && !$parentdom && &can_edit_quotas()) {
	print &ui_table_row($text{'edit_quota'},
		&ui_radio("quota_def", $d->{'quota'} ? 0 : 1,
		  [ [ 1, $text{'form_unlimit'} ],
		    [ 0, &quota_input("quota", $d->{'quota'}, "home") ] ]), 3,
		\@tds);

	print &ui_table_row($text{'edit_uquota'},
		&ui_radio("uquota_def", $d->{'uquota'} ? 0 : 1,
		  [ [ 1, $text{'form_unlimit'} ],
		    [ 0, &quota_input("uquota", $d->{'uquota'}, "home") ] ]), 3,
		\@tds);
	}

if ($config{'bw_active'} && !$parentdom) {
	# Show bandwidth limit and usage
	if (&can_edit_bandwidth()) {
		print &ui_table_row($text{'edit_bw'},
			    &bandwidth_input("bw", $d->{'bw_limit'}), 3, \@tds);
		}
	else {
		print &ui_table_row($text{'edit_bw'},
		  $d->{'bw_limit'} ?
		    &text('edit_bwpast_'.$config{'bw_past'},
		        &nice_size($d->{'bw_limit'}), $config{'bw_period'}) :
		    $text{'edit_bwnone'}, 3, \@tds);
		}
	}

# Show total disk usage, broken down into unix user and mail users
if (&has_home_quotas() && !$parentdom && $d->{'unix'}) {
	&show_domain_quota_usage($d);
	}

if ($config{'bw_active'} && !$parentdom) {
	# Show usage over current period
	&show_domain_bw_usage($d);
	}

if (!$parentdom) {
	print &ui_hidden_end();
	print &ui_table_end();
	}

# Show section for custom fields, if any
$fields = &show_custom_fields($d, \@tds);
if ($fields) {
	print &ui_hidden_table_start($text{'edit_customsect'}, "width=100%", 2,
				     "custom", 0);
	print $fields;
	print &ui_hidden_end();
	print &ui_table_end();
	}

# Show buttons for turning features on and off (if allowed)
print &ui_hidden_table_start($text{'edit_featuresect'}, "width=100%", 2,
			     "feature", 0);
if ($d->{'disabled'}) {
	# Disabled, so tell the user that features cannot be changed
	print &ui_table_row(undef,
	      "&nbsp;<br><font color=#ff0000>".
	      "<b>".$text{'edit_disabled_'.$d->{'disabled_reason'}}."\n".
	      $text{'edit_disabled'}."<br>".
	      ($d->{'disabled_why'} ?
		&text('edit_disabled_why', $d->{'disabled_why'}) : "").
	      "</b></font><br>&nbsp;</td>", 4);
	}
else {
	# Show features for this domain
	$ftable = "<table width=100%>";
	$i = 0;
	@dom_features = $aliasdom ? @opt_alias_features : @opt_features;
	foreach $f (@dom_features) {
		# Webmin feature is not needed for sub-servers
		next if ($d->{'parent'} && $f eq "webmin");

		# Unix feature is not needed for subdomains
		next if ($d->{'parent'} && $f eq "unix");

		# Cannot enable features not in alias
		next if ($aliasdom && !$aliasdom->{$f});

		# Don't show features that are always enabled, if currently set
		if ($config{$f} == 3 && $d->{$f}) {
			$ftable .= &ui_hidden($f, $d->{$f}),"\n";
			next;
			}

		$ftable .= "<tr>\n" if ($i%2 == 0);
		local $txt = $parentdom ? $text{'edit_sub'.$f} : undef;
		$txt ||= $text{'edit_'.$f};
		$w = $i%2 == 0 ? 30 : 70;
		$ftable .= "<td width=$w% align=left>";
		if (!&can_use_feature($f)) {
			$ftable .= &ui_checkbox($f."_dis", 1, undef,
						$d->{$f}, undef, 1);
			$ftable .= &ui_hidden($f, $d->{$f}),"\n";
			}
		else {
			$ftable .= &ui_checkbox($f, 1, "", $d->{$f}, undef,
					!$config{$f} && defined($config{$f}));
			}
		$ftable .= "<b>".&hlink($txt, $f)."</b>";
		$ftable .= "</td>\n";
		$ftable .= "</tr>\n" if ($i++%2 == 1);
		}

	foreach $f (@feature_plugins) {
		# Cannot enable features not in alias target
		next if ($aliasdom && !$aliasdom->{$f});

		next if (!&plugin_call($f, "feature_suitable",
					$parentdom, $aliasdom, $subdom));

		$ftable .= "<tr>\n" if ($i%2 == 0);
		$label = &plugin_call($f, "feature_label", 1);
		$w = $i%2 == 0 ? 30 : 70;
		$ftable .= "<td width=$w% align=left>";
		if (!&can_use_feature($f)) {
			$ftable .= &ui_checkbox($f."_dis", 1, "",
						       $d->{$f}, undef, 1);
			$ftable .= &ui_hidden($f, $d->{$f}),"\n";
			}
		else {
			$ftable .= &ui_checkbox($f, 1, "", $d->{$f});
			}
		$ftable .= "<b>$label</b></td>\n";
		$ftable .= "</tr>\n" if ($i++%2 == 1);
		}
	$ftable .= "</table>";

	print &ui_table_row(undef, $ftable, 4);
	}
print &ui_hidden_end();
print &ui_table_end();

# Save changes button
print &ui_form_end([ [ "save", $text{'edit_save'} ] ]);

# Show actions for this domain, unless the theme vetos it (cause they are on
# the left menu)
if ($current_theme ne "virtual-server-theme" &&
    !$main::basic_virtualmin_domain) {
	&show_domain_buttons($d);
	}

&ui_print_footer("", $text{'index_return'});

