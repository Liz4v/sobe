# Tutorial

This is the full onboarding walkthrough for Sobe: it takes you from "no AWS account"
all the way to publishing files on your own domain. If you already have a working
S3 bucket and CloudFront distribution, you can skip ahead to the "Install Sobe" section
below and the [Configuration](configuration.md) page.

## Warnings (is Sobe for you?)

Before you spend an afternoon on cloud console screens, make sure this is actually the
setup you want. The advantages of using the public cloud for a drop box are:

1. If you want, you may fully control the public address by using a domain you own.
2. Whatever public addresses you use are permanently yours as long you keep your
   domain (or your public cloud account if you don't use your own domain).
3. No worries about web server security as long as you only upload stuff meant to
   be public.

If you just want to share files that are currently interesting to you, or want some
kind of access control, I don't recommend Sobe. Use established file sharing services
such as Dropbox.com, Google Drive, Microsoft OneDrive. They are built for exactly that,
and Sobe is not: everything you publish through it is public to anyone with the URL.

Public cloud services **will** require your credit card, and often your ID too. This
tutorial will help you set up products with excellent free tiers that can field a small
but significant amount of traffic. If your files get a huge amount of traffic, you
**will** get a bill, but you can (and should) set a budget cap -- we do exactly that a
few steps below, so a surprise bill gets stopped while it is still pocket change.

I, the sole author of Sobe, am an AWS specialist, and that's why Sobe and this tutorial
are all-AWS. But if you already use a different public cloud service (GCP, Azure,
Cloudflare, Bunny.net, Scaleway, etc.), do open an issue explaining your setup because
I'm interested in expanding support.

## Create an AWS account

[Create an AWS account](https://aws.amazon.com/) if you don't have one yet; the sign-up
form walks you through the credit card and identity steps mentioned above. Once the
account exists, you will get access to the AWS console, the web interface where all of
the following sections happen.

The console's top bar has a search box; use it to search for AWS product names
(S3, CloudFront, IAM, ACM) instead of hunting through the enormous service menus.

Now, before creating anything else, go to Billing and Cost Management. Click Budgets.
Set a hard limit. This is the budget cap from the warnings section: it is the thing
standing between you and an unpleasant surprise if something you host suddenly gets
popular.

- A really low limit like $5 or $1 is the best place to start. You can always raise it
  later; you cannot retroactively lower a bill.
- An alert at 80% is also a good idea, so you hear about unusual traffic before the cap
  is reached.
- For scale: my drop box has never cost more than 4 cents in any individual month.

## Create a bucket

Search for S3 in the console. Once in S3, use the top right menu to select a region
for your bucket to live. I recommend using a region that is close to you.
If you don't care, use N. Virginia (us-east-1). Remember the region you chose.

Create a bucket. This is where your files will actually be stored.
Name it whatever. Bucket names are globally unique across all AWS customers,
so if the name you want is taken, use account regional namespace -- the console offers
it as a naming option and it scopes the name to your account and region instead of the
whole world.

Leave all remaining settings at default. The defaults keep the bucket private; that is
correct, because CloudFront (next section) will be the only thing reading from it
directly.

Finally, upload an example file through the console -- any small file will do. If you
have an index.html handy, that's even better. We will use it in the next section to
prove the distribution works before Sobe ever enters the picture.

## Create a CloudFront distribution

CloudFront is the CDN that will actually serve your files to the public. Search for
CloudFront in the console and create a distribution. Unlike the bucket, there is no
region to choose here: CloudFront is a global service (the console's region picker
switches to "Global"), and its edge locations serve your files everywhere regardless
of where the bucket lives.

On the pricing question: Free works. I have Pay-as-you-go because I set it up before
fixed plans existed, and I have never surpassed the free tier.

Name it whatever, "drop box" works. Copy-paste the name to the description. Don't set
the domain yet, we'll cover it later -- the custom-domain steps need a certificate that
doesn't exist yet.

For the origin (where CloudFront fetches content from), pick origin type Amazon S3. For
S3 origin, click Browse to find the bucket you just created.

Leave all remaining settings at default. S3 permissions will be automatically updated
for CloudFront, meaning AWS wires up the private bucket so that this distribution -- and
only this distribution -- can read it. You don't have to touch bucket policies yourself.

Once it is created, note the distribution ID (it looks like `E1111111111111`) and the
distribution domain name (it looks like `d2222222222222.cloudfront.net`). Both go into
Sobe's config file shortly.

Test your example file by requesting it through the distribution domain name -- e.g.
`https://d2222222222222.cloudfront.net/example.txt` for a file named `example.txt` at
the top of the bucket. If it downloads, your storage and CDN are working end to end.

This cloudfront.net subdomain is yours now. You can stick with it or, later in this
tutorial, I'll explain how to use your own domain.

## Install Sobe

With the AWS side standing, install the CLI. Install with `uv tool install sobe` or
`pip install sobe`, whichever works for you. I like
[uv](https://github.com/astral-sh/uv#installation).

Run `sobe` once. If no config file exists yet, it creates one and tells you where, then
exits so you can edit it.

Edit the config file: set `storage.bucket` to your bucket name and `cache.distribution`
to the distribution ID you noted above. Set `url` to your CloudFront domain name for now
(e.g. `https://d2222222222222.cloudfront.net/`) -- if you adopt a custom domain at the
end of this tutorial, you will come back and change it.

Save the config file. We will need that for our next section: the `sobe --policy`
command reads the bucket and distribution from it to generate exactly the permissions
Sobe needs.

## Create IAM (Identity and Access Management) access for Sobe

So far you have been acting as your account's root-level console user. Sobe should not
run with that kind of power; instead we create a dedicated IAM user that can touch only
your drop box. Search for IAM in the console. Like CloudFront, IAM is a global service:
users, policies, and access keys exist account-wide, so there is no region to pick in
this section either.

Click IAM users, Create user. Pick a username, e.g. `drop-box`. Leave everything blank
for now and just create the user -- no console password, no permission sets; we attach
a tailor-made policy next.

You'll be back to a user list. At the right, click Add permissions, Create inline
policy, JSON. The JSON editor wants a policy document, and Sobe writes it for you: run
`sobe --policy` in your terminal to get the JSON to fill up here. It grants upload,
delete, and list on your bucket plus cache invalidation on your distribution, and
nothing else.

Scroll down to click Next. Call the policy name "sobe" and click Create policy to
finish.

Now the user exists and has permissions, but Sobe still needs credentials to act as that
user. On the top right, click Create an access key, Other. Continue until you see
**Retrieve access keys**. You will need these keys -- this screen is the only time AWS
will show you the secret one, so copy both now.

Fill in `aws_access_key_id` and `aws_secret_access_key` into the
`[target.main.aws_session]` table in the config file. Don't forget to remove the `#`
prefixes -- the template ships those lines commented out. Also set your `region_name`
to the same region you created your S3 bucket in (told you to remember it).

Sobe should be fully functional now. Publish a file using it. If the upload prints a
URL and the URL works in your browser, everything below this point is optional polish.

## What will your domain be?

Everything so far serves files from the `d2222222222222.cloudfront.net` name AWS
assigned you. If you are happy with that, you are done. The rest of this tutorial gives
your drop box a name you chose yourself.

Domains are **not** free but they come on pretty cheap annual cost (unless you want an
expensive TLD like `.car`) and many registrars let you pay several years in advance,
just in case.

Use whatever registrar you like, except GoDaddy. GoDaddy is all dark patterns. Here's an
affiliate link with $2 off if you want to tip: <https://hover.com/Fb7kBrgy>

One structural decision matters here. If you want to use your apex domain (the bare
`example.com`), you will have to use Route53, which is $0.50/mo -- apex records can't be
CNAMEs, and Route53's alias records are the AWS answer to that. Otherwise you can use
your registrar's DNS server, which AFAIK is always included with the domain.

I use a subdomain (e.g. `files.example.com`) so I don't pay for Route53. All I need is a
CNAME record pointing my subdomain at the CloudFront domain name:

| Type  | Host    | Value                           |
|-------|---------|---------------------------------|
| CNAME | `files` | `d2222222222222.cloudfront.net` |

## Create an ACM Certificate

CloudFront serves HTTPS only, so before it will answer for your domain, you need a TLS
certificate for it -- free, from AWS Certificate Manager (ACM). For this one, region
must be us-east-1: ACM is a regional service, but CloudFront -- being global -- only
reads certificates from us-east-1, regardless of where your bucket lives. Switch the
console region before you start; this is the one section where the region is forced
on you.

Click Request, Request a public certificate, fill FQDN exactly right -- the fully
qualified domain name, e.g. `files.example.com`, exactly as users will type it. A typo
here means a certificate for the wrong name. Leave all remaining settings at default.

The new certificate will say Pending validation. ACM wants proof that you control the
domain before it signs anything, and the proof is a DNS record: in the Domains section
it's telling you what the records must look like. Example:

- Domain: `files.example.com`
- Status: Pending validation
- CNAME name: `_44444444444444444444444444444444.files.example.com.`
- CNAME value: `_55555555555555555555555555555555.jjjjjjjjjj.acm-validations.aws.`

Create the requested CNAME in your registrar. Note that the "Host" column is just the
part to the left of your domain -- registrars append `example.com` themselves. Your DNS
records now look like this:

```{eval-rst}
.. tabularcolumns:: |\X{2}{16}|\X{7}{16}|\X{7}{16}|
```

| Type  | Host                                      | Value                                                              |
|-------|-------------------------------------------|--------------------------------------------------------------------|
| CNAME | `_44444444444444444444444444444444.files` | `_55555555555555555555555555555555.jjjjjjjjjj.acm-validations.aws` |
| CNAME | `files`                                   | `d2222222222222.cloudfront.net`                                    |

You will usually have to wait for a few minutes until it works -- DNS propagation plus
ACM's checking interval. The status flips to Issued on its own.

Leave the validation there permanently so the certificate auto-renews. If you delete the
record, the certificate still works until it expires, and then renewal silently fails --
future you will not enjoy debugging that.

## Back to CloudFront

The last step is telling the distribution about its new name. Back in the CloudFront
console, click the distribution ID to see details. At the bottom center you will see an
empty list of Alternate domain names.

Click add domain, type the FQDN, select the certificate you just validated, complete.
The distribution will take a minute or two to update.

Test your own domain with your own drop box! Yay! Your example file should now load at
`https://files.example.com/...` just like it did on the cloudfront.net name.

Finally, edit your config file again to correct the public URL: set `url` to your own
domain (e.g. `https://files.example.com/`) so Sobe prints links people can actually use.
