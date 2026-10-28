import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState, type FormEvent, type ReactNode } from "react";

import { api } from "../api/client";
import { ApiError, errorMessage, unwrap } from "../api/errors";
import type { MemberProfile, MemberProfileUpdate, Role } from "../api/types";
import { ErrorMessage, Loading } from "../components/QueryStates";
import {
  FormField as Field,
  pageHeading,
  primaryButton,
  secondaryButton,
  sectionHeading,
} from "../components/ui";
import { ROLE_LABELS, ROLES } from "../format";
import { useActingMember, useSession } from "../session";

export function profileQueryKey(memberId: number) {
  return ["member", memberId] as const;
}

export function roleLabel(profile: Pick<MemberProfile, "is_manager" | "is_band_leader">): string {
  if (profile.is_manager) return "Manager";
  if (profile.is_band_leader) return "Band leader";
  return "Member";
}

export function ProfilePage() {
  const member = useActingMember();
  const [editing, setEditing] = useState(false);
  const profile = useQuery({
    queryKey: profileQueryKey(member.id),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/members/{member_id}", { params: { path: { member_id: member.id } } }),
      ),
  });

  return (
    <section>
      <h1 className={pageHeading}>Profile</h1>
      <div className="mt-4">
        {profile.isPending && <Loading label="Loading your profile…" />}
        {profile.isError && (
          <ErrorMessage
            message={errorMessage(profile.error)}
            onRetry={() => void profile.refetch()}
          />
        )}
        {profile.isSuccess &&
          (editing ? (
            <ProfileForm profile={profile.data} onDone={() => setEditing(false)} />
          ) : (
            <ProfileDetails profile={profile.data} onEdit={() => setEditing(true)} />
          ))}
      </div>
    </section>
  );
}

function ProfileDetails({ profile, onEdit }: { profile: MemberProfile; onEdit: () => void }) {
  const notSet = <span className="text-gray-600">Not set</span>;
  return (
    <>
      <div className="border border-gray-300 bg-paper p-4">
        <p className="text-xl font-semibold">{profile.name}</p>
        {/* The role is a word in a bordered mark, so it never depends on color. */}
        <p className="mt-2">
          <span className="inline-block border border-ink px-2 py-0.5 text-sm font-medium">
            {roleLabel(profile)}
          </span>
        </p>
        <dl className="mt-4 grid gap-x-6 gap-y-2 sm:grid-cols-[max-content_1fr]">
          <Detail term="Phone">{profile.phone ?? notSet}</Detail>
          <Detail term="Email">{profile.email ?? notSet}</Detail>
          <Detail term="Primary instrument">
            {profile.primary_role ? ROLE_LABELS[profile.primary_role] : notSet}
          </Detail>
          <Detail term="Secondary instrument">
            {profile.secondary_role ? ROLE_LABELS[profile.secondary_role] : notSet}
          </Detail>
        </dl>
      </div>
      <p className="mt-2 text-sm text-gray-700">Roles are fixed and can't be changed.</p>
      <button type="button" onClick={onEdit} className={`${primaryButton} mt-4`}>
        Edit profile
      </button>
    </>
  );
}

function Detail({ term, children }: { term: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-sm font-medium text-gray-700 sm:text-base sm:text-ink">{term}</dt>
      <dd className="mb-2 sm:mb-0">{children}</dd>
    </>
  );
}

// ---- Editing -----------------------------------------------------------------------------

interface ProfileValues {
  name: string;
  email: string;
  phone: string;
  primaryRole: Role | "";
  secondaryRole: Role | "";
}

type ProfileField = keyof ProfileValues;
type ProfileErrors = Partial<Record<ProfileField, string>>;

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function validateProfile(values: ProfileValues): ProfileErrors {
  const errors: ProfileErrors = {};
  if (!values.name.trim()) errors.name = "Enter your name.";
  if (!values.email.trim()) errors.email = "Enter your email address.";
  else if (!EMAIL_PATTERN.test(values.email.trim())) {
    errors.email = "Enter an email address like name@example.com.";
  }
  if (values.secondaryRole && values.secondaryRole === values.primaryRole) {
    errors.secondaryRole = "Choose a different instrument from your primary one.";
  }
  return errors;
}

function toBody(values: ProfileValues): MemberProfileUpdate {
  return {
    name: values.name.trim(),
    email: values.email.trim(),
    phone: values.phone.trim() || null,
    primary_role: values.primaryRole || null,
    secondary_role: values.secondaryRole || null,
  };
}

const FIELD_ORDER: ProfileField[] = ["name", "phone", "email", "primaryRole", "secondaryRole"];

// The server's business-rule refusals that belong to one field.
const SERVER_FIELD_ERRORS: Record<string, ProfileField> = {
  email_taken: "email",
  secondary_same_as_primary: "secondaryRole",
};

function ProfileForm({ profile, onDone }: { profile: MemberProfile; onDone: () => void }) {
  const member = useActingMember();
  const { signIn } = useSession();
  const queryClient = useQueryClient();
  const formId = useId();
  const [values, setValues] = useState<ProfileValues>({
    name: profile.name,
    email: profile.email ?? "",
    phone: profile.phone ?? "",
    primaryRole: profile.primary_role ?? "",
    secondaryRole: profile.secondary_role ?? "",
  });
  const [errors, setErrors] = useState<ProfileErrors>({});

  const save = useMutation({
    mutationFn: (body: MemberProfileUpdate) =>
      unwrap(
        api.PATCH("/api/v1/members/{member_id}", {
          params: { path: { member_id: profile.id } },
          body,
        }),
      ),
    onSuccess: (saved) => {
      queryClient.setQueryData(profileQueryKey(saved.id), saved);
      void queryClient.invalidateQueries({ queryKey: ["members"] });
      // The header shows who is acting, so keep the name there in step.
      signIn({ ...member, name: saved.name });
      onDone();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code in SERVER_FIELD_ERRORS) {
        setErrors({ [SERVER_FIELD_ERRORS[error.code]]: error.message });
      }
    },
  });

  function update(field: ProfileField, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const found = validateProfile(values);
    setErrors(found);
    const firstInvalid = FIELD_ORDER.find((field) => found[field]);
    if (firstInvalid) {
      // Take keyboard and screen reader users straight to the first problem.
      document.getElementById(fieldId(firstInvalid))?.focus();
      return;
    }
    save.mutate(toBody(values));
  }

  const fieldId = (field: ProfileField) => `${formId}-${field}`;
  const otherError =
    save.isError && !(save.error instanceof ApiError && save.error.code in SERVER_FIELD_ERRORS);

  return (
    <form onSubmit={submit} noValidate aria-labelledby={`${formId}-heading`}>
      <h2 id={`${formId}-heading`} className={sectionHeading}>
        Edit your details
      </h2>
      {otherError && (
        <div className="mt-3">
          <ErrorMessage message={errorMessage(save.error)} />
        </div>
      )}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Field
          id={fieldId("name")}
          label="Name"
          error={errors.name}
          input={(props) => (
            <input
              {...props}
              autoComplete="name"
              value={values.name}
              onChange={(event) => update("name", event.target.value)}
            />
          )}
        />
        <Field
          id={fieldId("phone")}
          label="Phone"
          hint="Optional. Only the manager and band leader see it."
          error={errors.phone}
          input={(props) => (
            <input
              {...props}
              type="tel"
              autoComplete="tel"
              value={values.phone}
              onChange={(event) => update("phone", event.target.value)}
            />
          )}
        />
        <Field
          id={fieldId("email")}
          label="Email"
          hint="Only the manager and band leader see it."
          error={errors.email}
          input={(props) => (
            <input
              {...props}
              type="email"
              autoComplete="email"
              value={values.email}
              onChange={(event) => update("email", event.target.value)}
            />
          )}
        />
        <div className="hidden sm:block" />
        <Field
          id={fieldId("primaryRole")}
          label="Primary instrument"
          error={errors.primaryRole}
          input={(props) => (
            <select
              {...props}
              value={values.primaryRole}
              onChange={(event) => update("primaryRole", event.target.value)}
            >
              <option value="">None</option>
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {ROLE_LABELS[role]}
                </option>
              ))}
            </select>
          )}
        />
        <Field
          id={fieldId("secondaryRole")}
          label="Secondary instrument"
          hint="Optional. Something else you can cover."
          error={errors.secondaryRole}
          input={(props) => (
            <select
              {...props}
              value={values.secondaryRole}
              onChange={(event) => update("secondaryRole", event.target.value)}
            >
              <option value="">None</option>
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {ROLE_LABELS[role]}
                </option>
              ))}
            </select>
          )}
        />
      </div>
      <p className="mt-4 text-sm text-gray-700">
        Role: <span className="font-medium text-ink">{roleLabel(profile)}</span>. Roles are fixed
        and can't be changed.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <button type="submit" className={primaryButton} disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save profile"}
        </button>
        <button type="button" className={secondaryButton} onClick={onDone}>
          Cancel
        </button>
      </div>
    </form>
  );
}
